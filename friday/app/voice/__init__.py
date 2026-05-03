from app.voice.stt_service import stt_service
from app.voice.tts_service import tts_service
from app.voice.emotion import detect_emotion
from app.voice.listener import VoiceListener, listener
from app.voice.native_tts import native_tts
from app.voice.vad import vad


async def voice_pipeline(audio: bytes) -> dict:
    text = await stt_service.transcribe(audio)
    emotion = detect_emotion(text)
    return {
        "text": text,
        "emotion": emotion,
    }
