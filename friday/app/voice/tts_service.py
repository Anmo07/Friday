import asyncio
import logging
from typing import AsyncGenerator
import edge_tts
from app.core.config import settings

logger = logging.getLogger(__name__)

class TTSService:
    """
    Conversational TTS Service (Kokoro-inspired efficiency).
    Target: Time-to-First-Audio (TTFA) < 200ms.
    Optimization: Yields MP3/WAV chunks immediately via async stream.
    """

    def __init__(self):
        # Using Jenny (Neural) for the most conversational Friday feel
        self._voice = "en-US-JennyNeural"
        self._rate = "+5%"  # Slightly faster for high-energy interaction
        self._pitch = "+0Hz"
        self._volume = "+0%"

    def set_voice(self, voice_name: str):
        self._voice = voice_name
        logger.info(f"TTS voice updated to: {voice_name}")

    async def stream_audio(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Streams audio chunks with sub-200ms TTFA.
        Compatible with Next.js frontend audio playback.
        """
        if not text:
            return

        try:
            # Clean text for smoother synthesis
            clean_text = text.replace("*", "").replace("#", "").strip()
            
            # Initiate Edge-TTS Communicate stream
            communicate = edge_tts.Communicate(
                clean_text, 
                self._voice, 
                rate=self._rate, 
                pitch=self._pitch,
                volume=self._volume
            )
            
            start_time = asyncio.get_event_loop().time()
            first_chunk_sent = False

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    if not first_chunk_sent:
                        ttfa = (asyncio.get_event_loop().time() - start_time) * 1000
                        logger.debug(f"TTS TTFA: {ttfa:.1f}ms")
                        first_chunk_sent = True
                    
                    yield chunk["data"]

        except Exception as e:
            logger.error(f"TTS Stream Error: {e}")

# Singleton
tts_service = TTSService()
