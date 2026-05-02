import asyncio
import logging
import struct
import math
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


class VoiceListener:
    def __init__(
        self,
        energy_threshold: float = 1200.0,
        silence_timeout: float = 0.8,
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
        self._ambient_energy = 0.0

    async def calibrate(self, duration: float = 1.0):
        """Sample ambient noise to set a baseline energy threshold"""
        try:
            import sounddevice as sd
            import numpy as np
            logger.info("Calibrating microphone... please be quiet.")
            
            # Record ambient noise
            recording = await asyncio.to_thread(
                sd.rec,
                frames=int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocking=True
            )
            
            # Calculate RMS of ambient noise
            rms = self._calculate_rms(recording.tobytes())
            self._ambient_energy = rms
            
            # Set threshold at 3.5x ambient RMS, but with a sane floor
            self.energy_threshold = max(rms * 3.5, 800.0)
            logger.info(f"Calibration complete. Ambient RMS: {rms:.0f}, New threshold: {self.energy_threshold:.0f}")
        except Exception as e:
            logger.warning(f"Calibration failed: {e}. Using default threshold: {self.energy_threshold}")

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
        
        # Auto-calibrate before starting
        await self.calibrate()
        
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
            import numpy as np
        except ImportError:
            logger.error("sounddevice/numpy not installed.")
            self._running = False
            return

        logger.info("Initializing neural acoustic monitor...")
        
        queue = asyncio.Queue()
        def audio_callback(indata, frames, time, status):
            queue.put_nowait(indata.copy())

        # Neural Monitor State
        self.current_rms = 0.0
        self.ambient_rms_rolling = self.energy_threshold
        last_clap_time = 0
        audio_buffer = []

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16', 
                              blocksize=self.chunk_size, callback=audio_callback):
                logger.info("InputStream active. Acoustic monitor live.")
                while self._running:
                    audio_chunk = await queue.get()
                    audio_bytes = audio_chunk.tobytes()
                    self.current_rms = self._calculate_rms(audio_bytes)
                    
                    # Update rolling ambient floor (slowly follow silence)
                    if self.current_rms < self.energy_threshold:
                        self.ambient_rms_rolling = self.ambient_rms_rolling * 0.95 + self.current_rms * 0.05

                    # Rolling buffer for wake word
                    audio_buffer.append(audio_bytes)
                    if len(audio_buffer) > 20: audio_buffer.pop(0)

                    # 1. Improved Double Clap Detection
                    # Look for spikes at least 3x the current rolling ambient floor
                    if self.current_rms > self.ambient_rms_rolling * 3.5:
                        now = time.time()
                        if 0.1 < (now - last_clap_time) < 0.7:
                            logger.info(f"Double Clap Detected (RMS: {self.current_rms:.0f}). Activating...")
                            full_audio = await self._capture_utterance_from_queue(queue, b"")
                            if full_audio and self._callback: await self._callback(full_audio)
                            last_clap_time = 0
                        else:
                            last_clap_time = now
                        # Skip wake word check if we're processing a clap
                        continue

                    # 2. Continuous Wake Word Verification
                    # Trigger STT only if energy is significantly above ambient
                    if self.current_rms > self.ambient_rms_rolling * 1.5 and len(audio_buffer) >= 8:
                        if await self._is_wake_word(b"".join(audio_buffer)):
                            logger.info(f"Wake Word Detected (RMS: {self.current_rms:.0f}).")
                            full_audio = await self._capture_utterance_from_queue(queue, b"")
                            if full_audio and self._callback: await self._callback(full_audio)
                            audio_buffer = [] 
                    
                    await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Acoustic monitor failed: {e}")
            self._running = False

    async def _capture_short_window(self, queue: asyncio.Queue, initial: bytes) -> bytes:
        """Capture ~1.5s of audio to check for wake word."""
        chunks = [initial]
        for _ in range(int(1.5 * self.sample_rate / self.chunk_size)):
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=0.2)
                chunks.append(chunk.tobytes())
            except: break
        return b"".join(chunks)

    async def _is_wake_word(self, audio_bytes: bytes) -> bool:
        from app.voice.stt_service import stt_service
        text = (await stt_service.transcribe(audio_bytes)).lower().strip()
        # Look for variations of the wake word
        return any(w in text for w in ["friday", "hey friday", "hi friday", "ready friday"])

    async def _capture_utterance_from_queue(self, queue: asyncio.Queue, initial_chunk: bytes, is_wake_clapped=False) -> Optional[bytes]:
        chunks = [initial_chunk] if initial_chunk else []
        silence_count = 0
        from core.pipeline import FridayPipeline
        from app.voice.stt_service import stt_service
        pipeline = FridayPipeline()
        
        # If clapped, we start fresh. If wake-word, we already have some audio.
        max_duration_chunks = int(12.0 * self.sample_rate / self.chunk_size)
        transcription_buffer = ""
        
        for i in range(max_duration_chunks):
            if not self._running: break
            try:
                audio_chunk = await asyncio.wait_for(queue.get(), timeout=1.0)
                audio_bytes = audio_chunk.tobytes()
                chunks.append(audio_bytes)
                
                if i > 0 and i % 20 == 0:
                    transcription_buffer = await stt_service.transcribe(b"".join(chunks))
                
                if len(transcription_buffer.strip()) > 5:
                    if await pipeline.turn_detector.predict_end_of_thought(audio_bytes, transcription_buffer):
                        break
                
                rms = self._calculate_rms(audio_bytes)
                if rms < self.energy_threshold * 0.4:
                    silence_count += 1
                    if silence_count >= int(self.silence_timeout * self.sample_rate / self.chunk_size):
                        break
                else:
                    silence_count = 0
            except: break
        
        return b"".join(chunks) if chunks else None

    @property
    def is_running(self) -> bool:
        return self._running


listener = VoiceListener()
