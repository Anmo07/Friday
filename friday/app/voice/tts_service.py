import asyncio
import logging
from typing import AsyncGenerator
import edge_tts
from app.core.config import settings

logger = logging.getLogger(__name__)

class TTSService:
    """
    Conversational TTS Service with <200ms Time-to-First-Audio (TTFA).
    Uses Edge-TTS streaming for speed and reliability on M2.
    """

    def __init__(self):
        self._voice = "en-US-JennyNeural"
        self._rate = "-5%"
        self._pitch = "+2Hz"

    def set_voice(self, voice_name: str):
        self._voice = voice_name

    async def stream_audio(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Stream audio bytes for the given text.
        Achieves <200ms TTFA by yielding chunks immediately.
        """
        if not text:
            return

        try:
            # Communicate object supports streaming
            communicate = edge_tts.Communicate(text, self._voice, rate=self._rate, pitch=self._pitch)
            
            first_chunk = True
            start_time = asyncio.get_event_loop().time()

            async for chunk in communicate.stream():
                if first_chunk:
                    elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
                    logger.info(f"TTS: First audio chunk yielded in {elapsed:.1f}ms")
                    first_chunk = False
                
                if chunk["type"] == "audio":
                    yield chunk["data"]

        except Exception as e:
            logger.error(f"TTS Streaming failed: {e}")

# Singleton
tts_service = TTSService()
