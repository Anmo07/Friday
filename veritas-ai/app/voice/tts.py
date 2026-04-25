"""Text-to-speech: Edge-TTS async, non-blocking."""
import logging

logger = logging.getLogger(__name__)


async def speak(text: str, voice: str = "en-US-JennyNeural") -> bytes:
    """Generate speech audio from text. Implemented in Task 6."""
    raise NotImplementedError("Implemented in Task 6")
