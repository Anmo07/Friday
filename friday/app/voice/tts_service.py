import asyncio
import logging
from typing import AsyncGenerator
import edge_tts
from app.core.config import settings
from app.voice.piper_service import piper_service
from app.voice.native_tts import native_tts

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self):
        self._voice = "en-US-JennyNeural"
        self._rate = "+5%"
        self._pitch = "+0Hz"
        self._volume = "+0%"
        self._lock = asyncio.Lock() # Lock to prevent multiple audio streams from interleaving
        self._interrupt_requested = False
        
        # Configure native TTS if available
        if settings.USE_NATIVE_TTS:
            native_tts.set_voice(settings.NATIVE_TTS_VOICE)
            native_tts.set_rate(settings.NATIVE_TTS_RATE)
            logger.info("TTS Engine: macOS Native (NSSpeechSynthesizer)")
        elif settings.USE_LOCAL_TTS or settings.PRIVACY_MODE:
            logger.info("TTS Engine: Piper (local)")
        else:
            logger.info("TTS Engine: Edge-TTS (cloud)")

    def interrupt(self):
        """Set interrupt flag to stop current playback"""
        self._interrupt_requested = True
        if settings.USE_NATIVE_TTS:
            native_tts.interrupt()
        logger.debug("TTS Interrupt requested")

    def _reset_interrupt(self):
        self._interrupt_requested = False

    def set_voice(self, voice_name: str):
        self._voice = voice_name
        if settings.USE_NATIVE_TTS:
            native_tts.set_voice(voice_name)
        logger.info(f"TTS voice updated to: {voice_name}")

    async def speak_direct(self, text: str):
        """
        Speak text directly through system speakers (native TTS only).
        This is the fastest path — zero file I/O, zero network.
        Falls back to stream_audio if native TTS unavailable.
        """
        if settings.USE_NATIVE_TTS:
            await native_tts.speak_aloud(text)
        else:
            # Fall back to streaming
            async for _ in self.stream_audio(text):
                pass

    async def synthesize_to_file(self, text: str):
        """
        Synthesize to a local audio file. Returns file path.
        Fastest path for menu bar integration with afplay.
        """
        if settings.USE_NATIVE_TTS:
            return await native_tts.synthesize_to_file(text)
        return None

    async def stream_audio(self, text: str) -> AsyncGenerator[bytes, None]:
        if not text:
            return
        
        # Priority 1: macOS Native TTS (fastest — <50ms)
        if settings.USE_NATIVE_TTS:
            logger.debug("Using macOS Native TTS engine")
            async for chunk in native_tts.stream_audio(text):
                yield chunk
            return
            
        # Priority 2: Piper local TTS
        if settings.USE_LOCAL_TTS or settings.PRIVACY_MODE:
            logger.debug("Using local Piper TTS engine")
            async for chunk in piper_service.stream_audio(text):
                yield chunk
            return
        
        # Priority 3: Edge-TTS (cloud)
        async with self._lock: # Acquire lock before starting stream
            self._reset_interrupt()
            try:
                clean_text = text.replace("*", "").replace("#", "").strip()
                communicate = edge_tts.Communicate(
                    clean_text,
                    self._voice,
                    rate=self._rate,
                    pitch=self._pitch,
                    volume=self._volume,
                )
                start_time = asyncio.get_event_loop().time()
                first_chunk_sent = False
                async for chunk in communicate.stream():
                    if self._interrupt_requested:
                        logger.info("TTS Stream interrupted mid-playback")
                        break
                    if chunk["type"] == "audio":
                        if not first_chunk_sent:
                            ttfa = (asyncio.get_event_loop().time() - start_time) * 1000
                            logger.debug(f"TTS TTFA: {ttfa:.1f}ms")
                            first_chunk_sent = True
                        yield chunk["data"]
            except asyncio.TimeoutError:
                logger.error("TTS Stream Timeout")
            except Exception as e:
                logger.error(f"TTS Stream Error: {e}")

    async def get_audio(self, text: str) -> bytes:
        audio_data = b""
        async for chunk in self.stream_audio(text):
            audio_data += chunk
        return audio_data


tts_service = TTSService()
