import asyncio
import logging
import os
import tempfile
import time
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self):
        self._model = None
        self._model_size = "large-v3-turbo"
        self._device = "cpu"
        self._compute_type = "int8"

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
                num_workers=2,
            )
            logger.info("Whisper Large V3 Turbo ready.")
        return self._model

    async def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""
        start_time = time.time()
        model = await asyncio.to_thread(self._get_model)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            segments, info = await asyncio.to_thread(
                model.transcribe,
                tmp_path,
                beam_size=1,
                language="en",
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                initial_prompt="Friday assistant loop.",
            )
            text = " ".join(segment.text.strip() for segment in segments)
            elapsed = time.time() - start_time
            logger.debug(f"STT Latency: {elapsed*1000:.0f}ms | Text: {text}")
            return text.strip()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    async def transcribe_stream(self, chunks: list[bytes]) -> str:
        if not chunks:
            return ""
        return await self.transcribe(b"".join(chunks))


stt_service = STTService()
