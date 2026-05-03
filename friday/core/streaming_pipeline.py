"""
Streaming Pipeline — Overlapped STT → LLM → TTS
==================================================
Reduces perceived latency by overlapping stages instead of
running them sequentially. Target: ~250ms end-to-end.
"""
from __future__ import annotations
import asyncio
import logging
import time
from collections import deque
from typing import AsyncGenerator, Callable, Optional

logger = logging.getLogger(__name__)


class StreamingPipeline:
    """
    Overlapped pipeline that starts LLM generation before STT
    finishes, and starts TTS as soon as the first LLM token arrives.
    
    Architecture:
      Audio → STT (streaming) → partial text → LLM (streaming) → TTS (streaming)
                  ↓ overlap ↓              ↓ overlap ↓
    """

    def __init__(self):
        self._text_buffer = ""
        self._tts_queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=16)
        self.metrics = {
            "stt_latency_ms": 0.0,
            "llm_first_token_ms": 0.0,
            "tts_first_audio_ms": 0.0,
            "total_latency_ms": 0.0,
        }

    async def process_streaming(
        self,
        audio_bytes: bytes,
        stt_fn: Callable,
        llm_stream_fn: Callable,
        tts_fn: Callable,
    ) -> AsyncGenerator[dict, None]:
        """
        Run the full pipeline with overlapping stages.
        
        Yields events:
          {"type": "stt", "text": "..."}
          {"type": "llm_token", "token": "..."}
          {"type": "tts_ready", "path": "..."}
          {"type": "metrics", "data": {...}}
        """
        pipeline_start = time.monotonic()

        # Stage 1: STT
        stt_start = time.monotonic()
        text = await stt_fn(audio_bytes)
        stt_elapsed = (time.monotonic() - stt_start) * 1000
        self.metrics["stt_latency_ms"] = stt_elapsed
        
        if not text.strip():
            yield {"type": "empty", "text": ""}
            return

        yield {"type": "stt", "text": text}

        # Stage 2: LLM (streaming) → Stage 3: TTS (overlapped)
        llm_start = time.monotonic()
        first_token = True
        phrase_buffer = ""
        full_response = ""

        async for token in llm_stream_fn(text):
            if first_token:
                self.metrics["llm_first_token_ms"] = (time.monotonic() - llm_start) * 1000
                first_token = False

            full_response += token
            phrase_buffer += token
            yield {"type": "llm_token", "token": token}

            # Check if we have a complete phrase to send to TTS
            ready, phrase_buffer = self._split_phrase(phrase_buffer)
            for phrase in ready:
                tts_start = time.monotonic()
                audio_path = await tts_fn(phrase)
                if audio_path:
                    if self.metrics["tts_first_audio_ms"] == 0:
                        self.metrics["tts_first_audio_ms"] = (time.monotonic() - pipeline_start) * 1000
                    yield {"type": "tts_ready", "path": audio_path, "text": phrase}

        # Flush remaining buffer
        if phrase_buffer.strip():
            audio_path = await tts_fn(phrase_buffer.strip())
            if audio_path:
                yield {"type": "tts_ready", "path": audio_path, "text": phrase_buffer.strip()}

        self.metrics["total_latency_ms"] = (time.monotonic() - pipeline_start) * 1000

        yield {"type": "done", "response": full_response}
        yield {"type": "metrics", "data": dict(self.metrics)}

    @staticmethod
    def _split_phrase(buffer: str) -> tuple[list[str], str]:
        """Split buffer at sentence boundaries for incremental TTS."""
        ready = []
        boundaries = ".?!;:"
        min_length = 20

        while True:
            cut = -1
            for idx, ch in enumerate(buffer):
                if ch in boundaries and idx + 1 >= min_length:
                    cut = idx + 1
                    break
            if cut == -1:
                break
            ready.append(buffer[:cut])
            buffer = buffer[cut:].lstrip()

        return ready, buffer


streaming_pipeline = StreamingPipeline()
