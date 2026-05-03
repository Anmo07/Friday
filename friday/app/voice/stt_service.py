import asyncio
import logging
import time
import numpy as np
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self):
        self._model = None
        self._fun_model = None
        self._mlx_stt = None
        self._model_size = settings.STT_MODEL_SIZE
        self._device = settings.STT_DEVICE
        self._compute_type = settings.STT_COMPUTE_TYPE
        self._num_workers = 2
        self._engine = settings.STT_ENGINE

    def _get_mlx_stt(self):
        """Lazy-load MLX-Whisper engine."""
        if self._mlx_stt is None:
            from app.voice.mlx_stt import MLXWhisperSTT
            logger.info(f"Loading MLX-Whisper ({self._model_size})...")
            self._mlx_stt = MLXWhisperSTT(model_size=self._model_size)
        return self._mlx_stt

    def _get_model(self):
        if self._engine == "funasr":
            return self._get_fun_model()
        if self._model is None:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper {self._model_size}...")
            self._model = WhisperModel(self._model_size, device=self._device, compute_type=self._compute_type)
        return self._model

    def _get_fun_model(self):
        if self._fun_model is None:
            from funasr import AutoModel
            logger.info("Loading Fun-ASR (SenseVoiceSmall) for high-noise robustness...")
            self._fun_model = AutoModel(model="iic/SenseVoiceSmall", device=self._device)
        return self._fun_model

    async def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""
        
        # Phase 2: Audio-Native E2E Intelligence
        # Check if we should bypass traditional STT and use Audio-Native engine
        if settings.AUDIO_NATIVE_ENGINE == "vibevoice":
            # Mocking E2E tokenization
            logger.info("Using VibeVoice 7.5Hz tokenizers for Audio-Native Tier.")
            # In a real impl, this would return speech tokens or a special identifier
            # for the pipeline to handle as E2E.
        
        start_time = time.time()

        # Route to the correct engine
        if self._engine == "mlx":
            text = await self._transcribe_mlx(audio_bytes)
        elif self._engine == "funasr":
            text = await self._transcribe_funasr(audio_bytes)
        else:
            text = await self._transcribe_whisper(audio_bytes)

        elapsed = time.time() - start_time
        logger.debug(f"STT Latency: {elapsed*1000:.0f}ms | Engine: {self._engine} | Text: {text}")
        
        # Tracking telemetry for STT stage - Avoid initializing heavy pipeline if not needed
        try:
            from core.observability import TelemetryManager
            telemetry = TelemetryManager()
            telemetry.track_query_efficiency("tier_1_stt", f"{self._engine}-{self._model_size}", elapsed * 1000)
        except Exception as e:
            logger.debug(f"Telemetry tracking skipped: {e}")
        
        return text.strip()

    async def _transcribe_mlx(self, audio_bytes: bytes) -> str:
        """Transcribe using MLX-Whisper (Metal-accelerated)."""
        try:
            mlx_stt = self._get_mlx_stt()
            return await mlx_stt.transcribe(audio_bytes)
        except Exception as e:
            logger.warning(f"MLX-Whisper failed, falling back to Faster-Whisper: {e}")
            return await self._transcribe_whisper(audio_bytes)

    async def _transcribe_funasr(self, audio_bytes: bytes) -> str:
        """Transcribe using FunASR."""
        try:
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception as e:
            logger.error(f"Audio pre-processing error: {e}")
            return ""
        
        model = await asyncio.to_thread(self._get_fun_model)
        res = await asyncio.to_thread(model.generate, input=audio_np, cache={}, language="auto", use_itn=True)
        return res[0]['text']

    async def _transcribe_whisper(self, audio_bytes: bytes) -> str:
        """Transcribe using Faster-Whisper (CTranslate2)."""
        # Audio Pre-processing: Convert int16 PCM to float32 numpy array [-1.0, 1.0]
        try:
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception as e:
            logger.error(f"Audio pre-processing error: {e}")
            return ""

        model = await asyncio.to_thread(self._get_model)

        async def _run_transcription(vad_enabled: bool):
            segments, info = await asyncio.to_thread(
                model.transcribe,
                audio_np,
                beam_size=1,
                language="en",
                vad_filter=vad_enabled,
                vad_parameters=dict(min_silence_duration_ms=250),
                initial_prompt="Friday assistant loop.",
            )
            return " ".join(segment.text.strip() for segment in segments)

        # First attempt with VAD filter on
        text = await _run_transcription(vad_enabled=True)
        
        # VAD Fallback: If transcription is empty, retry once with vad_filter=False
        if not text.strip():
            logger.debug("VAD filtered all audio. Retrying with VAD disabled...")
            text = await _run_transcription(vad_enabled=False)

        return text

    async def transcribe_stream(self, chunks: list[bytes]) -> str:
        if not chunks:
            return ""
        return await self.transcribe(b"".join(chunks))

    def set_engine(self, engine: str):
        """Switch STT engine at runtime (mlx, whisper, funasr)."""
        if engine in ("mlx", "whisper", "funasr"):
            self._engine = engine
            logger.info(f"STT engine switched to: {engine}")

    def set_model_size(self, model_size: str):
        """Switch model size at runtime (for battery-aware scaling)."""
        self._model_size = model_size
        if self._mlx_stt:
            self._mlx_stt.set_model(model_size)
        logger.info(f"STT model size switched to: {model_size}")


stt_service = STTService()
