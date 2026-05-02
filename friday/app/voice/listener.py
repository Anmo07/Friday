from __future__ import annotations

import asyncio
import base64
import json
import logging
import math
import os
import struct
import subprocess
import time
from collections import deque
from pathlib import Path
from typing import Awaitable, Callable, Optional

import numpy as np

try:
    import torch
    import torch.nn.functional as torch_f
    from funasr import AutoModel
except ImportError:
    torch = None
    torch_f = None
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
        self.mic_gain = 1.5 # 50% boost

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callback: Optional[Callable[[bytes], Awaitable[None]]] = None
        self._ambient_energy = 0.0
        self.current_rms = 0.0
        self.current_peak = 0.0
        self.ambient_peak_rolling = energy_threshold
        self.ambient_rms_rolling = energy_threshold

        self.profile_path = Path(
            os.getenv(
                "FRIDAY_VOICE_PROFILE_PATH",
                str(Path.home() / ".friday" / "voice_profile.json"),
            )
        )
        self.keychain_service = os.getenv(
            "FRIDAY_VOICE_KEYCHAIN_SERVICE", "ai.friday.voice-profile"
        )
        self.keychain_account = os.getenv(
            "FRIDAY_VOICE_KEYCHAIN_ACCOUNT", "authorized-speaker"
        )
        self.sv_model_id = os.getenv(
            "FRIDAY_SV_MODEL", "iic/speech_campplus_sv_en_voxceleb_16k"
        )
        self.sv_similarity_threshold = float(
            os.getenv("FRIDAY_SV_THRESHOLD", "0.45")
        )
        self.min_verification_seconds = float(
            os.getenv("FRIDAY_SV_MIN_SECONDS", "0.80")
        )
        self.min_snr_db = float(os.getenv("FRIDAY_SV_MIN_SNR_DB", "6.0"))
        self.verification_post_roll = float(
            os.getenv("FRIDAY_SV_POST_ROLL_SECONDS", "0.70")
        )
        self.audio_buffer_seconds = float(
            os.getenv("FRIDAY_AUDIO_BUFFER_SECONDS", "1.60")
        )
        self.wake_eval_cooldown = float(
            os.getenv("FRIDAY_WAKE_EVAL_COOLDOWN_SECONDS", "0.35")
        )
        self.audio_queue_max_chunks = int(
            os.getenv("FRIDAY_AUDIO_QUEUE_MAX_CHUNKS", "64")
        )

        self.user_embedding = None
        self.sv_model = None
        self._sv_model_lock = asyncio.Lock()

        self._load_user_profile()

    @property
    def has_voice_profile(self) -> bool:
        return self.user_embedding is not None

    def _run_keychain_command(self, args: list[str]) -> Optional[str]:
        if os.name != "posix" or not sys_platform_is_macos():
            return None
        try:
            result = subprocess.run(
                ["security", *args],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return None
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            if stderr and "could not be found" not in stderr.lower():
                logger.debug("Keychain command failed: %s", stderr)
            return None
        return result.stdout.strip()

    def _load_user_profile(self):
        if torch is None:
            logger.warning(
                "PyTorch is unavailable. Speaker verification will fail closed until dependencies are installed."
            )
            return

        payload = self._read_profile_payload()
        if not payload:
            logger.info("No enrolled voice profile found. Friday will remain locked.")
            return

        try:
            embedding = torch.tensor(payload["embedding"], dtype=torch.float32)
            self.user_embedding = self._normalize_embedding(embedding)
            logger.info("Authorized voice profile loaded.")
        except Exception as exc:
            logger.error("Failed to load voice profile: %s", exc)
            self.user_embedding = None

    def _read_profile_payload(self) -> Optional[dict]:
        payload = self._read_profile_from_keychain()
        if payload is not None:
            return payload

        if not self.profile_path.exists():
            return None

        try:
            return json.loads(self.profile_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Failed to read fallback voice profile file: %s", exc)
            return None

    def _read_profile_from_keychain(self) -> Optional[dict]:
        raw = self._run_keychain_command(
            [
                "find-generic-password",
                "-a",
                self.keychain_account,
                "-s",
                self.keychain_service,
                "-w",
            ]
        )
        if not raw:
            return None

        try:
            decoded = base64.b64decode(raw.encode("utf-8")).decode("utf-8")
            return json.loads(decoded)
        except Exception as exc:
            logger.error("Failed to decode keychain voice profile: %s", exc)
            return None

    def _store_profile_payload(self, payload: dict):
        encoded = base64.b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8")

        stored_in_keychain = False
        if sys_platform_is_macos():
            stored_in_keychain = (
                self._run_keychain_command(
                    [
                        "add-generic-password",
                        "-U",
                        "-a",
                        self.keychain_account,
                        "-s",
                        self.keychain_service,
                        "-w",
                        encoded,
                    ]
                )
                is not None
            )

        if stored_in_keychain:
            logger.info("Voice profile stored in macOS Keychain.")
            return

        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile_path.write_text(
            json.dumps(payload, separators=(",", ":")), encoding="utf-8"
        )
        os.chmod(self.profile_path, 0o600)
        logger.warning(
            "Voice profile stored in %s with 0600 permissions because Keychain storage was unavailable.",
            self.profile_path,
        )

    async def _ensure_sv_model(self):
        if self.sv_model is not None:
            return
        if AutoModel is None:
            raise RuntimeError("FunASR is not installed")

        async with self._sv_model_lock:
            if self.sv_model is not None:
                return

            def _load():
                logger.info(
                    "Loading FunASR speaker model %s on CPU.",
                    self.sv_model_id,
                )
                return AutoModel(model=self.sv_model_id, device="cpu")

            self.sv_model = await asyncio.to_thread(_load)

    def _normalize_embedding(self, embedding):
        if torch is None or torch_f is None:
            raise RuntimeError("PyTorch is required for speaker verification")
        tensor = embedding.detach().float().cpu()
        return torch_f.normalize(tensor, dim=0)

    async def _compute_embedding(self, audio_np: np.ndarray):
        await self._ensure_sv_model()

        def _infer():
            return self.sv_model.generate(input=audio_np, sample_rate=self.sample_rate)

        result = await asyncio.to_thread(_infer)
        return self._extract_embedding(result)

    def _extract_embedding(self, result):
        if isinstance(result, list) and result:
            result = result[0]
        if not isinstance(result, dict):
            raise ValueError("Unexpected FunASR speaker verification output")

        for key in ("spk_embedding", "embedding", "sv_embedding"):
            if key in result:
                return self._normalize_embedding(
                    torch.tensor(result[key], dtype=torch.float32)
                )
        raise ValueError("Speaker embedding was not present in FunASR output")

    def _prepare_verification_audio(
        self, audio_bytes: bytes, *, enrollment: bool = False
    ) -> tuple[np.ndarray, dict]:
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        if audio_np.size == 0:
            return np.empty(0, dtype=np.float32), {
                "duration_s": 0.0,
                "speech_ratio": 0.0,
                "snr_db": -math.inf,
            }

        audio_np /= 32768.0
        voiced_audio = self._trim_to_voiced_segments(audio_np)
        if voiced_audio.size == 0:
            voiced_audio = audio_np

        duration_s = voiced_audio.size / self.sample_rate
        speech_ratio = min(1.0, voiced_audio.size / max(audio_np.size, 1))
        speech_rms = float(np.sqrt(np.mean(np.square(voiced_audio)))) if voiced_audio.size else 0.0
        noise_floor = max(self.ambient_rms_rolling / 32768.0, 1e-4)
        snr_db = 20.0 * math.log10((speech_rms + 1e-6) / noise_floor)

        if voiced_audio.size:
            peak = float(np.max(np.abs(voiced_audio)))
            if peak > 0.98:
                voiced_audio = voiced_audio / peak * 0.98

        meta = {
            "duration_s": duration_s,
            "speech_ratio": speech_ratio,
            "snr_db": snr_db,
        }

        if not enrollment:
            if duration_s < self.min_verification_seconds:
                return np.empty(0, dtype=np.float32), meta
            if speech_ratio < 0.20:
                return np.empty(0, dtype=np.float32), meta
            if snr_db < self.min_snr_db:
                return np.empty(0, dtype=np.float32), meta

        return voiced_audio.astype(np.float32, copy=False), meta

    def _trim_to_voiced_segments(self, audio_np: np.ndarray) -> np.ndarray:
        frame_size = max(1, int(0.030 * self.sample_rate))
        hop_size = max(1, int(0.015 * self.sample_rate))
        pad = int(0.100 * self.sample_rate)

        if audio_np.size <= frame_size:
            return audio_np

        ambient_floor = max(self.ambient_rms_rolling / 32768.0, 0.0025)
        speech_threshold = max(ambient_floor * 2.25, 0.008)
        segments: list[tuple[int, int]] = []

        for start in range(0, audio_np.size - frame_size + 1, hop_size):
            frame = audio_np[start : start + frame_size]
            frame_rms = float(np.sqrt(np.mean(np.square(frame))))
            if frame_rms >= speech_threshold:
                seg_start = max(0, start - pad)
                seg_end = min(audio_np.size, start + frame_size + pad)
                if segments and seg_start <= segments[-1][1]:
                    segments[-1] = (segments[-1][0], max(segments[-1][1], seg_end))
                else:
                    segments.append((seg_start, seg_end))

        if not segments:
            return np.empty(0, dtype=np.float32)

        return np.concatenate([audio_np[start:end] for start, end in segments])

    async def verify_speaker(self, audio_bytes: bytes) -> bool:
        if self.user_embedding is None:
            logger.info("Voice profile missing. Allowing trigger in unsecure mode.")
            return True

        if AutoModel is None or torch is None:
            logger.error("FunASR or PyTorch is unavailable. Speaker verification failed closed.")
            return False

        try:
            verification_audio, meta = self._prepare_verification_audio(audio_bytes)
            if verification_audio.size == 0:
                logger.info(
                    "Speaker verification skipped: insufficient speech (duration=%.2fs, speech_ratio=%.2f, snr=%.1fdB).",
                    meta["duration_s"],
                    meta["speech_ratio"],
                    meta["snr_db"],
                )
                return False

            current_embedding = await self._compute_embedding(verification_audio)
            similarity = torch_f.cosine_similarity(
                current_embedding.unsqueeze(0),
                self.user_embedding.unsqueeze(0),
            ).item()
            logger.info(
                "Speaker verification score %.3f (threshold %.3f).",
                similarity,
                self.sv_similarity_threshold,
            )
            return similarity >= self.sv_similarity_threshold
        except Exception as exc:
            logger.error("Speaker verification failed: %s", exc)
            return False

    async def capture_user_profile(self, duration: int = 6):
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("sounddevice is required for voice enrollment") from exc

        if AutoModel is None or torch is None:
            raise RuntimeError("FunASR speaker verification dependencies are not installed")

        logger.info("Recording %ss of enrollment audio for authorized speaker.", duration)
        recording = await asyncio.to_thread(
            sd.rec,
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocking=True,
        )

        prepared_audio, meta = self._prepare_verification_audio(
            recording.tobytes(), enrollment=True
        )
        if prepared_audio.size < int(self.sample_rate * self.min_verification_seconds):
            raise RuntimeError(
                "Enrollment audio did not contain enough voiced speech. Record again in a quieter room."
            )

        window = int(1.6 * self.sample_rate)
        hop = int(0.8 * self.sample_rate)
        embeddings = []

        for start in range(0, max(prepared_audio.size - window, 0) + 1, hop):
            chunk = prepared_audio[start : start + window]
            if chunk.size < int(self.sample_rate * self.min_verification_seconds):
                continue
            embeddings.append(await self._compute_embedding(chunk))

        if not embeddings:
            embeddings.append(await self._compute_embedding(prepared_audio))

        self.user_embedding = self._normalize_embedding(torch.stack(embeddings).mean(dim=0))
        payload = {
            "version": 1,
            "model_id": self.sv_model_id,
            "sample_rate": self.sample_rate,
            "similarity_threshold": self.sv_similarity_threshold,
            "created_at": int(time.time()),
            "speech_ratio": meta["speech_ratio"],
            "snr_db": meta["snr_db"],
            "embedding": self.user_embedding.tolist(),
        }
        self._store_profile_payload(payload)
        logger.info("Voice profile capture complete.")

    async def calibrate(self, duration: float = 1.0):
        try:
            import sounddevice as sd
        except ImportError as exc:
            logger.warning(
                "Calibration skipped because sounddevice is unavailable: %s",
                exc,
            )
            return

        logger.info("Calibrating microphone for %.1fs of ambient audio.", duration)
        try:
            recording = await asyncio.to_thread(
                sd.rec,
                frames=int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocking=True,
            )
            rms = self._calculate_rms(recording.tobytes()) * self.mic_gain
            if rms < 10.0:
                logger.warning("Calibration detected near-silent background. Check microphone permissions.")
                rms = 200.0 # Safety floor
            self._ambient_energy = rms
            self.ambient_rms_rolling = max(rms, 1.0)
            self.ambient_peak_rolling = max(
                float(np.max(np.abs(recording))),
                rms * 2.0,
                1.0,
            )
            self.energy_threshold = max(rms * 2.5, 300.0)
            logger.info(
                "Calibration complete. Ambient RMS %.0f, threshold %.0f.",
                rms,
                self.energy_threshold,
            )
        except Exception as exc:
            logger.warning(
                "Calibration failed: %s. Keeping threshold %.0f.",
                exc,
                self.energy_threshold,
            )

    @staticmethod
    def _calculate_rms(audio_chunk: bytes) -> float:
        if len(audio_chunk) < 2:
            return 0.0
        count = len(audio_chunk) // 2
        shorts = struct.unpack(f"{count}h", audio_chunk[: count * 2])
        sum_squares = sum(sample * sample for sample in shorts)
        return math.sqrt(sum_squares / count) if count else 0.0

    def _resample(self, data: np.ndarray, input_rate: int) -> np.ndarray:
        if input_rate == self.sample_rate:
            return data.astype(np.int16, copy=False)
        duration = len(data) / float(input_rate)
        output_len = max(1, int(duration * self.sample_rate))
        return np.interp(
            np.linspace(0.0, duration, output_len, endpoint=False),
            np.linspace(0.0, duration, len(data), endpoint=False),
            data,
        ).astype(np.int16)

    async def start(self, callback: Callable[[bytes], Awaitable[None]]):
        if self._running:
            logger.warning("Voice listener already running.")
            return

        await self.calibrate()
        self._callback = callback
        self._running = True
        self._task = asyncio.create_task(self._listen_loop())
        logger.info("Voice listener started.")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._callback = None
        logger.info("Voice listener stopped.")

    async def _listen_loop(self):
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice is not installed. Voice listener cannot start.")
            self._running = False
            return

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[np.ndarray] = asyncio.Queue(
            maxsize=self.audio_queue_max_chunks
        )

        def _enqueue_frame(frame: np.ndarray):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(frame)
            except asyncio.QueueFull:
                pass

        def audio_callback(indata, frames, callback_time, status):
            if status:
                logger.debug("Microphone callback status: %s", status)
            loop.call_soon_threadsafe(_enqueue_frame, indata.copy())

        self.current_rms = 0.0
        self.current_peak = 0.0
        self.ambient_peak_rolling = max(self.ambient_peak_rolling, 1.0)
        self.ambient_rms_rolling = max(self.ambient_rms_rolling, self._ambient_energy, 1.0)

        last_clap_time = 0.0
        last_wake_eval = 0.0
        audio_buffer = deque(
            maxlen=max(1, int((self.audio_buffer_seconds * self.sample_rate) / self.chunk_size) + 2)
        )

        hw_sample_rate = int(sd.query_devices(kind="input")["default_samplerate"])
        logger.info("Opening input stream at %sHz.", hw_sample_rate)

        try:
            with sd.InputStream(
                samplerate=hw_sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.chunk_size,
                callback=audio_callback,
            ):
                logger.info(
                    "Input stream active. Waiting for double clap or wake phrase."
                )
                while self._running:
                    raw_chunk = await queue.get()
                    audio_chunk = self._resample(raw_chunk.flatten(), hw_sample_rate)
                    audio_bytes = audio_chunk.tobytes()

                    self.current_peak = float(np.max(np.abs(raw_chunk)))
                    self.current_rms = self._calculate_rms(audio_bytes) * self.mic_gain

                    if self.current_rms < self.energy_threshold * 1.25:
                        self.ambient_rms_rolling = (
                            self.ambient_rms_rolling * 0.98 + self.current_rms * 0.02
                        )
                    if self.current_peak < self.energy_threshold * 2.0:
                        self.ambient_peak_rolling = (
                            self.ambient_peak_rolling * 0.98 + self.current_peak * 0.02
                        )

                    audio_buffer.append(audio_bytes)

                    if self.current_peak > max(self.ambient_peak_rolling * 4.0, self.energy_threshold * 2.5):
                        now = time.monotonic()
                        if 0.08 < (now - last_clap_time) < 0.8:
                            trigger_audio = b"".join(audio_buffer)
                            verification_audio, seed_audio = await self._collect_verification_window(
                                queue,
                                trigger_audio,
                                hw_sample_rate,
                            )
                            if await self.verify_speaker(verification_audio):
                                full_audio = await self._capture_utterance_from_queue(
                                    queue,
                                    seed_audio,
                                    hw_sample_rate,
                                )
                                if full_audio and self._callback:
                                    await self._callback(full_audio)
                            last_clap_time = 0.0
                            audio_buffer.clear()
                            continue
                        last_clap_time = now

                    now = time.monotonic()
                    if (
                        self.current_rms > self.energy_threshold
                        and len(audio_buffer) >= 8
                        and (now - last_wake_eval) >= self.wake_eval_cooldown
                    ):
                        last_wake_eval = now
                        trigger_audio = b"".join(audio_buffer)
                        if await self._is_wake_word(trigger_audio):
                            verification_audio, seed_audio = await self._collect_verification_window(
                                queue,
                                trigger_audio,
                                hw_sample_rate,
                            )
                            if await self.verify_speaker(verification_audio):
                                full_audio = await self._capture_utterance_from_queue(
                                    queue,
                                    seed_audio,
                                    hw_sample_rate,
                                )
                                if full_audio and self._callback:
                                    await self._callback(full_audio)
                            audio_buffer.clear()
                    await asyncio.sleep(0.005)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Acoustic monitor failed: %s", exc)
            self._running = False
            try:
                import rumps

                rumps.notification(
                    "Friday Error",
                    "Microphone Access Failed",
                    "Check microphone permissions and audio device ownership.",
                )
            except Exception:
                pass

    async def _collect_verification_window(
        self,
        queue: asyncio.Queue[np.ndarray],
        pre_roll_audio: bytes,
        hw_rate: int,
    ) -> tuple[bytes, bytes]:
        extra_frames_target = int(self.verification_post_roll * self.sample_rate)
        extra_audio: list[bytes] = []
        collected_frames = 0

        while collected_frames < extra_frames_target and self._running:
            try:
                raw_chunk = await asyncio.wait_for(queue.get(), timeout=0.20)
            except asyncio.TimeoutError:
                break
            resampled = self._resample(raw_chunk.flatten(), hw_rate)
            chunk_bytes = resampled.tobytes()
            extra_audio.append(chunk_bytes)
            collected_frames += len(resampled)

        pre_roll_tail_bytes = int(0.30 * self.sample_rate) * 2
        seed_audio = pre_roll_audio[-pre_roll_tail_bytes:] + b"".join(extra_audio)
        return pre_roll_audio + seed_audio, seed_audio

    async def _is_wake_word(self, audio_bytes: bytes) -> bool:
        try:
            from .stt_service import stt_service
        except Exception as exc:
            logger.error("Wake-word STT import failed: %s", exc)
            return False

        text = (await stt_service.transcribe(audio_bytes)).lower().strip()
        return any(
            wake_phrase in text
            for wake_phrase in ("friday", "hey friday", "hi friday", "okay friday")
        )

    async def _capture_utterance_from_queue(
        self,
        queue: asyncio.Queue[np.ndarray],
        initial_audio: bytes,
        hw_rate: int = 16000,
    ) -> Optional[bytes]:
        chunks = [initial_audio] if initial_audio else []
        silence_count = 0
        max_duration_chunks = int(12.0 * hw_rate / self.chunk_size)
        silence_limit = max(2, int(self.silence_timeout * hw_rate / self.chunk_size))

        for _ in range(max_duration_chunks):
            if not self._running:
                break
            try:
                raw_chunk = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                break

            resampled = self._resample(raw_chunk.flatten(), hw_rate)
            audio_bytes = resampled.tobytes()
            chunks.append(audio_bytes)

            rms = self._calculate_rms(audio_bytes)
            if rms < max(self.ambient_rms_rolling * 1.2, self.energy_threshold * 0.35):
                silence_count += 1
                if silence_count >= silence_limit:
                    break
            else:
                silence_count = 0

        return b"".join(chunks) if chunks else None

    @property
    def is_running(self) -> bool:
        return self._running


def sys_platform_is_macos() -> bool:
    return os.uname().sysname == "Darwin" if hasattr(os, "uname") else False


listener = VoiceListener()
