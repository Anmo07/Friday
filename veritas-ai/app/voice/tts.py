"""Text-to-speech: Edge-TTS async, non-blocking."""
import asyncio
import logging
import tempfile
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Voice profiles
VOICE_PROFILES = {
    "friday": "en-US-JennyNeural",
    "jarvis": "en-GB-RyanNeural",
    "assistant": "en-US-AriaNeural",
    "calm": "en-US-GuyNeural",
}

# Current voice setting
_current_voice: str = "en-US-JennyNeural"


def set_voice(profile: str):
    """Set TTS voice by profile name."""
    global _current_voice
    if profile in VOICE_PROFILES:
        _current_voice = VOICE_PROFILES[profile]
        logger.info(f"Voice set to: {profile} ({_current_voice})")
    else:
        logger.warning(f"Unknown voice profile: {profile}, keeping {_current_voice}")


async def speak(text: str, voice: Optional[str] = None) -> bytes:
    """
    Generate speech audio from text using Edge-TTS.
    Returns MP3 audio bytes. Non-blocking async operation.
    """
    if not text:
        return b""

    voice = voice or _current_voice
    tmp_path = None

    try:
        import edge_tts

        communicate = edge_tts.Communicate(text, voice)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        logger.debug(f"TTS generated {len(audio_bytes)} bytes for {len(text)} chars")
        return audio_bytes

    except ImportError:
        logger.error("edge-tts not installed. Install with: pip install edge-tts")
        return b""
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        return b""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
