import asyncio
import logging
import time
import numpy as np
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self):
        self._model = None
        self._model_size = "large-v3-turbo"
        self._device = "cpu"
        self._compute_type = "int8"
        self._num_workers = 2

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            logger.info(
                f"Loading Whisper {self._model_size} ({self._compute_type}) on {self._device}..."
            )
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
                cpu_threads=4,
                num_workers=self._num_workers,
            )
            logger.info("Whisper Large V3 Turbo ready.")
        return self._model

    async def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""
        
        start_time = time.time()
        model = await asyncio.to_thread(self._get_model)
        
        # Audio Pre-processing: Convert int16 PCM to float32 numpy array [-1.0, 1.0]
        try:
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception as e:
            logger.error(f"Audio pre-processing error: {e}")
            return ""

        async def _run_transcription(vad_enabled: bool):
            segments, info = await asyncio.to_thread(
                model.transcribe,
                audio_np,
                beam_size=1,
                language="en",
                vad_filter=vad_enabled,
                vad_parameters=dict(min_silence_duration_ms=250),
                initial_prompt="Friday assistant loop.",
            )
            return " ".join(segment.text.strip() for segment in segments)

        # First attempt with VAD filter on
        text = await _run_transcription(vad_enabled=True)
        
        # VAD Fallback: If transcription is empty, retry once with vad_filter=False
        if not text.strip():
            logger.debug("VAD filtered all audio. Retrying with VAD disabled...")
            text = await _run_transcription(vad_enabled=False)

        elapsed = time.time() - start_time
        logger.debug(f"STT Latency: {elapsed*1000:.0f}ms | Text: {text}")
        return text.strip()

    async def transcribe_stream(self, chunks: list[bytes]) -> str:
        if not chunks:
            return ""
        return await self.transcribe(b"".join(chunks))


stt_service = STTService()
