"""
MLX-Whisper STT Engine — Apple Silicon Optimized
=================================================
Metal-accelerated speech-to-text using Apple's MLX framework.
Runs 2-3x faster than CTranslate2 (Faster-Whisper) on M1/M2/M3/M4.

Supports:
  - Full transcription (batch mode)
  - Model size selection (tiny, base, small, medium, large)
  - Automatic fallback to Faster-Whisper if MLX is unavailable

Latency: ~200ms for base.en (vs ~600ms for Faster-Whisper on CPU)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Lazy import flags
_mlx_whisper = None
_mlx_available: Optional[bool] = None


def _check_mlx_available() -> bool:
    """Check if mlx-whisper is installed and usable."""
    global _mlx_whisper, _mlx_available
    if _mlx_available is not None:
        return _mlx_available

    try:
        import mlx_whisper
        _mlx_whisper = mlx_whisper
        _mlx_available = True
        logger.info("MLX-Whisper is available — using Metal-accelerated STT.")
    except ImportError:
        _mlx_available = False
        logger.warning("MLX-Whisper not installed. Will fall back to Faster-Whisper.")

    return _mlx_available


class MLXWhisperSTT:
    """
    Apple Silicon-optimized STT using MLX-Whisper.

    Model naming:
      - "tiny.en", "base.en", "small.en" → English-only (faster)
      - "tiny", "base", "small", "medium", "large-v3-turbo" → Multilingual

    Recommended:
      - base.en  → Best speed/accuracy for English (~200ms on M1 Max)
      - small.en → Better accuracy, slightly slower (~300ms)
      - tiny.en  → Ultra-fast, lower accuracy (~100ms)
    """

    # Map model sizes to HuggingFace paths for mlx-whisper
    MODEL_MAP = {
        "tiny": "mlx-community/whisper-tiny-mlx",
        "tiny.en": "mlx-community/whisper-tiny.en-mlx",
        "base": "mlx-community/whisper-base-mlx",
        "base.en": "mlx-community/whisper-base.en-mlx",
        "small": "mlx-community/whisper-small-mlx",
        "small.en": "mlx-community/whisper-small.en-mlx",
        "medium": "mlx-community/whisper-medium-mlx",
        "medium.en": "mlx-community/whisper-medium.en-mlx",
        "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    }

    def __init__(self, model_size: str = "base.en"):
        self._model_size = model_size
        self._model_path = self.MODEL_MAP.get(model_size, model_size)
        self._loaded = False
        self._warmup_done = False

    def _ensure_loaded(self):
        """
        MLX-Whisper loads the model on first transcription call,
        but we can trigger it early to avoid cold-start latency.
        """
        if not self._loaded and _check_mlx_available():
            logger.info("Pre-warming MLX-Whisper model: %s", self._model_path)
            # Transcribe a tiny silent buffer to trigger model download/load
            try:
                silence = np.zeros(16000, dtype=np.float32)  # 1 second of silence
                _mlx_whisper.transcribe(
                    silence,
                    path_or_hf_repo=self._model_path,
                    language="en",
                )
                self._loaded = True
                logger.info("MLX-Whisper model %s is ready.", self._model_size)
            except Exception as e:
                logger.warning("MLX-Whisper pre-warm failed: %s", e)

    async def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio bytes (int16 PCM, 16kHz mono) to text.

        Returns empty string on failure or empty input.
        """
        if not audio_bytes:
            return ""

        if not _check_mlx_available():
            return await self._fallback_transcribe(audio_bytes)

        start_time = time.monotonic()

        # Convert int16 PCM → float32 [-1.0, 1.0]
        try:
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception as e:
            logger.error("Audio pre-processing error: %s", e)
            return ""

        if audio_np.size < 1600:  # Less than 100ms of audio
            logger.debug("Audio too short for transcription (%d samples)", audio_np.size)
            return ""

        def _run_transcription():
            result = _mlx_whisper.transcribe(
                audio_np,
                path_or_hf_repo=self._model_path,
                language="en",
                word_timestamps=False,
                condition_on_previous_text=False,
                # Performance tuning for Apple Silicon
                fp16=True,
                compression_ratio_threshold=2.4,
                no_speech_threshold=0.6,
                # Additional optimizations
                beam_size=1,  # Greedy decoding for speed
                patience=1.0,  # Minimal beam search patience
                length_penalty=1.0,
            )
            return result.get("text", "").strip()

        try:
            text = await asyncio.to_thread(_run_transcription)
        except Exception as e:
            logger.error("MLX-Whisper transcription failed: %s", e)
            return await self._fallback_transcribe(audio_bytes)

        elapsed = (time.monotonic() - start_time) * 1000
        logger.debug("MLX-Whisper Latency: %.0fms | Model: %s | Text: %s", elapsed, self._model_size, text)

        return text

    async def transcribe_stream(self, chunks: list[bytes]) -> str:
        """Transcribe a list of audio chunks by joining them."""
        if not chunks:
            return ""
        return await self.transcribe(b"".join(chunks))

    async def _fallback_transcribe(self, audio_bytes: bytes) -> str:
        """Fall back to Faster-Whisper if MLX is not available."""
        logger.debug("Falling back to Faster-Whisper for transcription.")
        try:
            from app.voice.stt_service import stt_service
            return await stt_service.transcribe(audio_bytes)
        except Exception as e:
            logger.error("Fallback transcription also failed: %s", e)
            return ""

    def set_model(self, model_size: str):
        """Switch the model (e.g. for battery-aware scaling)."""
        if model_size != self._model_size:
            self._model_size = model_size
            self._model_path = self.MODEL_MAP.get(model_size, model_size)
            self._loaded = False
            logger.info("MLX-Whisper model switched to: %s", model_size)


# Module-level singleton
mlx_stt = MLXWhisperSTT()
