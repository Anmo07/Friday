"""Voice pipeline: STT, TTS, emotion detection, continuous listener."""
from app.voice.stt import transcribe
from app.voice.tts import speak, set_voice
from app.voice.emotion import detect_emotion
from app.voice.listener import VoiceListener, listener


async def voice_pipeline(audio: bytes) -> dict:
    """
    Full voice pipeline: Audio -> STT -> Query -> TTS -> Audio.
    Note: Query processing is handled by the caller (API layer).
    This function handles the voice I/O parts only.
    """
    text = await transcribe(audio)
    emotion = detect_emotion(text)
    return {
        "text": text,
        "emotion": emotion,
    }
