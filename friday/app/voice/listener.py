import asyncio
import logging
import time
import struct
import math
import os
import numpy as np
from typing import Optional, Callable, Awaitable

try:
    import torch
    from funasr import AutoModel
except ImportError:
    torch = None
    AutoModel = None

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
        self.current_rms = 0.0
        self.current_peak = 0.0
        self.ambient_peak_rolling = energy_threshold
        self.ambient_rms_rolling = energy_threshold

        # Speaker Verification State
        self.profile_path = os.path.expanduser("~/.friday/user_voice_profile.pt")
        self.user_embedding = None
        self.sv_model = None
        self.ambient_rms_rolling = energy_threshold
        self._load_user_profile()

    def _load_user_profile(self):
        """Loads the authorized user's voice embedding."""
        if os.path.exists(self.profile_path):
            try:
                self.user_embedding = torch.load(self.profile_path)
                logger.info(f"Authorized voice profile loaded from {self.profile_path}")
            except Exception as e:
                logger.error(f"Failed to load voice profile: {e}")

    def _init_sv_model(self):
        """Lazy-load the Fun-ASR Speaker Verification model."""
        if self.sv_model is None and AutoModel is not None:
            logger.info("Initializing Fun-ASR CAM++ Speaker Verification Model (speech_campplus_sv_en_16k_common)...")
            self.sv_model = AutoModel(model="damo/speech_campplus_sv_en_16k_common", device="cpu")

    async def verify_speaker(self, audio_bytes: bytes) -> bool:
        """Compares current audio against the authorized embedding."""
        if self.user_embedding is None:
            logger.warning("No voice profile found. Verification skipped (Security Gap).")
            return True
        
        # Load model if needed
        await asyncio.to_thread(self._init_sv_model)
        
        try:
            # Convert PCM to float32 for model consumption
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            res = await asyncio.to_thread(self.sv_model.generate, input=audio_np, sample_rate=16000)
            current_emb = torch.tensor(res[0]['spk_embedding'])
            
            # Cosine Similarity check
            similarity = torch.nn.functional.cosine_similarity(current_emb.unsqueeze(0), self.user_embedding.unsqueeze(0)).item()
            logger.info(f"Speaker Verification Score: {similarity:.4f}")
            
            # Optimized threshold for far-field/noise: 0.25 - 0.30
            return similarity > 0.28
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False

    async def capture_user_profile(self, duration: int = 5):
        """Capture reference embedding from microphone."""
        import sounddevice as sd
        logger.info(f"Recording {duration}s of voice for profile... Please speak clearly.")
        recording = await asyncio.to_thread(
            sd.rec, int(duration * 16000), samplerate=16000, channels=1, dtype='int16', blocking=True
        )
        
        await asyncio.to_thread(self._init_sv_model)
        audio_np = recording.flatten().astype(np.float32) / 32768.0
        res = await asyncio.to_thread(self.sv_model.generate, input=audio_np, sample_rate=16000)
        self.user_embedding = torch.tensor(res[0]['spk_embedding'])
        
        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        torch.save(self.user_embedding, self.profile_path)
        logger.info(f"Voice profile saved to {self.profile_path}")

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
        self.current_peak = 0.0
        self.ambient_peak_rolling = self.energy_threshold
        last_clap_time = 0
        audio_buffer = []

        hw_sample_rate = int(sd.query_devices(kind='input')['default_samplerate'])
        logger.info(f"Opening hardware stream at {hw_sample_rate}Hz...")

        def resample(data, input_rate, output_rate):
            import numpy as np
            if input_rate == output_rate: return data
            duration = len(data) / input_rate
            output_len = int(duration * output_rate)
            return np.interp(np.linspace(0, duration, output_len), np.linspace(0, duration, len(data)), data).astype(np.int16)

        try:
            with sd.InputStream(samplerate=hw_sample_rate, channels=1, dtype='int16', 
                              blocksize=self.chunk_size, callback=audio_callback):
                logger.info("InputStream active. Waiting for Double Clap or 'Hey Friday'...")
                while self._running:
                    raw_chunk = await queue.get()
                    audio_chunk = resample(raw_chunk.flatten(), hw_sample_rate, self.sample_rate)
                    audio_bytes = audio_chunk.tobytes()
                    
                    # 1. PEAK DETECTION for Transients (Claps)
                    # Claps are sharp spikes, RMS blurs them. Peak captures them.
                    self.current_peak = np.max(np.abs(raw_chunk))
                    self.current_rms = self._calculate_rms(audio_bytes)
                    
                    if self.current_peak < self.energy_threshold * 2:
                        self.ambient_peak_rolling = self.ambient_peak_rolling * 0.98 + self.current_peak * 0.02

                    audio_buffer.append(audio_bytes)
                    if len(audio_buffer) > 25: audio_buffer.pop(0) # ~1.5s buffer

                    # Double Clap Logic: Peak must be 4x the rolling ambient peak
                    if self.current_peak > self.ambient_peak_rolling * 4.0:
                        now = time.time()
                        if 0.08 < (now - last_clap_time) < 0.8:
                            logger.info(f"Double Clap Triggered! (Peak: {self.current_peak:.0f})")
                            
                            # Verification before capture
                            trigger_audio = b"".join(audio_buffer)
                            if await self.verify_speaker(trigger_audio):
                                full_audio = await self._capture_utterance_from_queue(queue, b"", hw_rate=hw_sample_rate)
                                if full_audio and self._callback: await self._callback(full_audio)
                            else:
                                logger.info("Unauthorized clap or transient rejected.")
                            
                            last_clap_time = 0
                        else:
                            last_clap_time = now
                        continue

                    # 2. Wake Word Logic: RMS-based
                    if self.current_rms > self.energy_threshold and len(audio_buffer) >= 10:
                        trigger_audio = b"".join(audio_buffer)
                        if await self._is_wake_word(trigger_audio):
                            logger.info(f"Voice Trigger: 'Friday' detected.")
                            
                            # Verification gate
                            if await self.verify_speaker(trigger_audio):
                                full_audio = await self._capture_utterance_from_queue(queue, b"", hw_rate=hw_sample_rate)
                                if full_audio and self._callback: await self._callback(full_audio)
                            else:
                                logger.info("Unauthorized speaker rejected.")
                            
                            audio_buffer = [] 
                    
                    await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Acoustic monitor failed: {e}")
            self._running = False
            import rumps
            rumps.notification("Friday Error", "Microphone Access Failed", "Please ensure no other app is using the mic and permissions are granted.")

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

    async def _capture_utterance_from_queue(self, queue: asyncio.Queue, initial_chunk: bytes, hw_rate: int = 16000) -> Optional[bytes]:
        chunks = [initial_chunk] if initial_chunk else []
        silence_count = 0
        from core.pipeline import FridayPipeline
        from app.voice.stt_service import stt_service
        import numpy as np
        pipeline = FridayPipeline()
        
        def resample(data, input_rate, output_rate):
            if input_rate == output_rate: return data
            duration = len(data) / input_rate
            output_len = int(duration * output_rate)
            return np.interp(np.linspace(0, duration, output_len), np.linspace(0, duration, len(data)), data).astype(np.int16)

        max_duration_chunks = int(12.0 * hw_rate / self.chunk_size)
        
        for i in range(max_duration_chunks):
            if not self._running: break
            try:
                raw_chunk = await asyncio.wait_for(queue.get(), timeout=1.0)
                # Resample each chunk to 16k
                audio_chunk = resample(raw_chunk.flatten(), hw_rate, self.sample_rate)
                audio_bytes = audio_chunk.tobytes()
                chunks.append(audio_bytes)
                
                # Check for end of thought
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
