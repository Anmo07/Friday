import asyncio
import logging
import struct
import math
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


class VoiceListener:
    def __init__(
        self,
        energy_threshold: float = 1000.0,
        silence_timeout: float = 2.0,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
    ):
        self.energy_threshold = energy_threshold
        self.silence_timeout = silence_timeout
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callback: Optional[Callable[[bytes], Awaitable]] = None

    @staticmethod
    def _calculate_rms(audio_chunk: bytes) -> float:
        if len(audio_chunk) < 2:
            return 0.0
        count = len(audio_chunk) // 2
        shorts = struct.unpack(f"{count}h", audio_chunk[: count * 2])
        sum_squares = sum(s * s for s in shorts)
        return math.sqrt(sum_squares / count) if count > 0 else 0.0

    async def start(self, callback: Callable[[bytes], Awaitable]):
        if self._running:
            logger.warning("Listener already running")
            return
        self._callback = callback
        self._running = True
        self._task = asyncio.create_task(self._listen_loop())
        logger.info("Voice listener started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Voice listener stopped")

    async def _listen_loop(self):
        try:
            import sounddevice as sd
        except ImportError:
            logger.error(
                "sounddevice not installed. Install with: pip install sounddevice"
            )
            self._running = False
            return
        logger.info(
            f"Listening for wake trigger (energy threshold: {self.energy_threshold})..."
        )
        while self._running:
            try:
                audio_data = await asyncio.to_thread(
                    sd.rec,
                    frames=self.chunk_size,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="int16",
                    blocking=True,
                )
                if audio_data is None:
                    continue
                audio_bytes = audio_data.tobytes()
                rms = self._calculate_rms(audio_bytes)
                if rms > self.energy_threshold:
                    logger.info(f"Wake detected! RMS={rms:.0f}")
                    full_audio = await self._capture_utterance(sd)
                    if full_audio and self._callback:
                        await self._callback(full_audio)
                await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listener error: {e}")
                await asyncio.sleep(1.0)

    async def _capture_utterance(self, sd) -> Optional[bytes]:
        chunks = []
        silence_count = 0
        max_silence_chunks = int(
            self.silence_timeout * self.sample_rate / self.chunk_size
        )
        max_duration_chunks = int(10.0 * self.sample_rate / self.chunk_size)
        for _ in range(max_duration_chunks):
            if not self._running:
                break
            try:
                audio_data = await asyncio.to_thread(
                    sd.rec,
                    frames=self.chunk_size,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="int16",
                    blocking=True,
                )
                if audio_data is None:
                    break
                audio_bytes = audio_data.tobytes()
                chunks.append(audio_bytes)
                rms = self._calculate_rms(audio_bytes)
                if rms < self.energy_threshold * 0.3:
                    silence_count += 1
                    if silence_count >= max_silence_chunks:
                        break
                else:
                    silence_count = 0
            except Exception as e:
                logger.error(f"Capture error: {e}")
                break
        if chunks:
            return b"".join(chunks)
        return None

    @property
    def is_running(self) -> bool:
        return self._running


listener = VoiceListener()
