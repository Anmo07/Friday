"""
Lightweight Speaker Verification — ONNX Resemblyzer
====================================================
10x lighter than FunASR for speaker verification.
Uses cosine similarity on speaker embeddings.
Falls back to FunASR if ONNX model not available.
"""
from __future__ import annotations
import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

_ort = None
try:
    import onnxruntime as ort
    _ort = ort
except ImportError:
    pass


class LightweightSpeakerVerifier:
    """ONNX-based speaker verification (~30ms vs FunASR ~200ms)."""

    def __init__(self, threshold: Optional[float] = None):
        # Use config threshold if not provided
        if threshold is None:
            try:
                from app.core.config import settings
                threshold = getattr(settings, 'SPEAKER_VERIFICATION_THRESHOLD', 0.7)
            except (ImportError, AttributeError):
                threshold = 0.7
        
        self.threshold = threshold
        self._session = None
        self._user_embedding: Optional[np.ndarray] = None
        self._model_path = str(Path.home() / ".friday" / "resemblyzer.onnx")
        self._embedding_path = str(Path.home() / ".friday" / "user_embedding.npy")
        self._load_user_embedding()

    def _load_user_embedding(self):
        if os.path.exists(self._embedding_path):
            try:
                self._user_embedding = np.load(self._embedding_path)
                logger.info("Loaded user speaker embedding.")
            except Exception as e:
                logger.warning("Failed to load speaker embedding: %s", e)

    def _get_session(self):
        if self._session is None and _ort and os.path.exists(self._model_path):
            self._session = _ort.InferenceSession(self._model_path)
            logger.info("ONNX speaker verification model loaded.")
        return self._session

    @property
    def is_available(self) -> bool:
        return (self._user_embedding is not None and 
                _ort is not None and 
                os.path.exists(self._model_path))

    async def verify(self, audio_np: np.ndarray) -> bool:
        if self._user_embedding is None:
            return True  # No profile = allow (unsecured mode)
        
        session = self._get_session()
        if session is None:
            return True  # Model not available = allow

        start = time.monotonic()
        try:
            def _infer():
                inp = audio_np.reshape(1, -1).astype(np.float32)
                embedding = session.run(None, {"input": inp})[0].flatten()
                norm_e = embedding / (np.linalg.norm(embedding) + 1e-8)
                norm_u = self._user_embedding / (np.linalg.norm(self._user_embedding) + 1e-8)
                return float(np.dot(norm_e, norm_u))

            similarity = await asyncio.to_thread(_infer)
            elapsed = (time.monotonic() - start) * 1000
            logger.info("Speaker verification: %.3f (threshold %.3f) in %.0fms",
                       similarity, self.threshold, elapsed)
            return similarity >= self.threshold
        except Exception as e:
            logger.error("Speaker verification failed: %s", e)
            return False

    async def enroll(self, audio_np: np.ndarray):
        session = self._get_session()
        if session is None:
            raise RuntimeError("ONNX model not available for enrollment")
        
        def _compute():
            inp = audio_np.reshape(1, -1).astype(np.float32)
            embedding = session.run(None, {"input": inp})[0].flatten()
            return embedding / (np.linalg.norm(embedding) + 1e-8)

        self._user_embedding = await asyncio.to_thread(_compute)
        os.makedirs(os.path.dirname(self._embedding_path), exist_ok=True)
        np.save(self._embedding_path, self._user_embedding)
        logger.info("Speaker embedding enrolled and saved.")


speaker_verifier = LightweightSpeakerVerifier()
