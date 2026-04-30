import asyncio
import logging
import os
import tempfile
import time
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class STTService:
    """
    Optimized STT Service using Whisper Large V3 Turbo.
    Optimized for Apple Silicon (M2) using Faster-Whisper.
    """

    def __init__(self):
        self._model = None
        self._model_size = "large-v3-turbo" # User requested Large V3 Turbo
        self._device = "cpu" # ctranslate2 (faster-whisper) is highly optimized for M2 CPU
        self._compute_type = "int8" # Best for memory-constrained M2 (8-16GB)

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper {self._model_size} on {self._device}...")
            # Load model with optimizations for M2
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
                cpu_threads=4, # M2 has 4 performance cores
                num_workers=2
            )
            logger.info("Whisper model loaded.")
        return self._model

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe full audio segment."""
        if not audio_bytes:
            return ""
        
        start_time = time.time()
        model = await asyncio.to_thread(self._get_model)
        
        # Temporary file for whisper
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # beam_size=1 for maximum speed (user wants sub-500ms total)
            segments, info = await asyncio.to_thread(
                model.transcribe, 
                tmp_path, 
                beam_size=1, 
                language="en",
                initial_prompt="Friday, assistant, boss."
            )
            
            text = " ".join(segment.text.strip() for segment in segments)
            duration = info.duration
            elapsed = time.time() - start_time
            rtfx = duration / elapsed if elapsed > 0 else 0
            
            logger.info(f"STT: '{text}' (Duration: {duration:.2f}s, Processed in: {elapsed:.2f}s, RTFx: {rtfx:.1f})")
            return text.strip()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    async def transcribe_stream(self, audio_queue: asyncio.Queue) -> str:
        """
        Placeholder for real-time streaming transcription.
        In production, this would use a sliding window of audio chunks.
        """
        all_bytes = []
        while not audio_queue.empty():
            all_bytes.append(await audio_queue.get())
        
        if not all_bytes:
            return ""
        return await self.transcribe(b"".join(all_bytes))

# Singleton
stt_service = STTService()
