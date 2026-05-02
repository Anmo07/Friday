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
        
        # Access the AntigravityPipeline singleton for Semantic Turn Detection
        from core.pipeline import FridayPipeline
        from app.voice.stt_service import stt_service
        pipeline = FridayPipeline()
        
        max_duration_chunks = int(10.0 * self.sample_rate / self.chunk_size)
        transcription_buffer = ""
        
        for i in range(max_duration_chunks):
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
                
                # Periodically update transcription buffer for semantic turn detection
                if i > 0 and i % 10 == 0: # Every ~600ms
                    transcription_buffer = await stt_service.transcribe(b"".join(chunks))
                
                # Phase 1: Semantic Turn Detection
                is_turn_complete = await pipeline.turn_detector.predict_end_of_thought(
                    audio_bytes, transcription_buffer
                )
                
                if is_turn_complete and len(transcription_buffer.strip()) > 0:
                    logger.info(f"Semantic Turn Detected. Transcription: {transcription_buffer}")
                    break
                
                rms = self._calculate_rms(audio_bytes)
                if rms < self.energy_threshold * 0.3:
                    silence_count += 1
                    if silence_count >= int(self.silence_timeout * self.sample_rate / self.chunk_size):
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
