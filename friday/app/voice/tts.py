"""Text-to-speech: local-first TTS with optional Edge-TTS fallback."""
import asyncio
import logging
import tempfile
import os
from typing import Optional

from app.core.config import settings

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
    if settings.TTS_PROVIDER == "pyttsx3":
        audio = await asyncio.to_thread(_speak_with_pyttsx3, text, voice)
        if audio:
            return audio

    return await _speak_with_edge_tts(text, voice)


def _speak_with_pyttsx3(text: str, voice: str) -> bytes:
    """Offline/local speech using system voices via pyttsx3."""
    tmp_path = None
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", settings.TTS_SPEECH_RATE)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as f:
            return f.read()
    except ImportError:
        logger.warning("pyttsx3 not installed. Falling back to edge-tts.")
        return b""
    except Exception as e:  # pragma: no cover - depends on local audio stack
        logger.warning("Local pyttsx3 TTS failed: %s", e)
        return b""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def _speak_with_edge_tts(text: str, voice: str) -> bytes:
    tmp_path = None
    try:
        import edge_tts
        
        # Use plain text for maximum compatibility
        communicate = edge_tts.Communicate(text, voice, rate="-5%", pitch="+2Hz")
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        
        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
            
        logger.debug("Edge-TTS generated %d bytes", len(audio_bytes))
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
