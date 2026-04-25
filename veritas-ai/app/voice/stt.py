"""Speech-to-text: Faster-Whisper with lazy model loading."""
import asyncio
import logging
import tempfile
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded model singleton
_model = None
_model_lock = asyncio.Lock()


def _get_or_load_model():
    """Lazy-load Faster-Whisper model on first use."""
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info("Loading Faster-Whisper model (tiny)...")
            _model = WhisperModel("tiny", compute_type="int8", device="cpu")
            logger.info("Faster-Whisper model loaded")
        except ImportError:
            logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
            raise
    return _model


def _transcribe_sync(audio_bytes: bytes) -> str:
    """Synchronous transcription using Faster-Whisper."""
    model = _get_or_load_model()

    # Write audio bytes to temp file (faster-whisper needs file path)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        segments, info = model.transcribe(tmp_path, beam_size=1, language="en")
        text = " ".join(segment.text.strip() for segment in segments)
        return text.strip()
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def transcribe(audio_bytes: bytes) -> str:
    """
    Transcribe audio bytes to text.
    Runs Faster-Whisper in thread pool to avoid blocking event loop.
    """
    if not audio_bytes:
        return ""
    return await asyncio.to_thread(_transcribe_sync, audio_bytes)
