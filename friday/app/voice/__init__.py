from app.voice.stt import transcribe
from app.voice.tts import speak, set_voice
from app.voice.emotion import detect_emotion
from app.voice.listener import VoiceListener, listener


async def voice_pipeline(audio: bytes) -> dict:
    text = await transcribe(audio)
    emotion = detect_emotion(text)
    return {
        "text": text,
        "emotion": emotion,
    }
