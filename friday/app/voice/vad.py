"""
Voice Activity Detection (VAD)
"""
from __future__ import annotations
import logging
import numpy as np

logger = logging.getLogger(__name__)

_webrtcvad = None
try:
    import webrtcvad
    _webrtcvad = webrtcvad
except ImportError:
    pass


class VoiceActivityDetector:
    def __init__(self, aggressiveness: int = 2, energy_threshold: float = 500.0,
                 min_speech_frames: int = 3, sample_rate: int = 16000):
        self.energy_threshold = energy_threshold
        self.min_speech_frames = min_speech_frames
        self.sample_rate = sample_rate
        self._speech_count = 0
        self._silence_count = 0
        self._ambient_energy = energy_threshold * 0.5
        self._webrtc_vad = None
        if _webrtcvad:
            try:
                self._webrtc_vad = _webrtcvad.Vad(aggressiveness)
            except Exception:
                pass

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        if audio_chunk.dtype == np.float32:
            audio_int16 = (audio_chunk * 32768.0).astype(np.int16)
        else:
            audio_int16 = audio_chunk.astype(np.int16)

        if self._webrtc_vad and audio_int16.size >= int(self.sample_rate * 0.03):
            frame_size = int(self.sample_rate * 0.03)
            frame = audio_int16[:frame_size]
            try:
                return self._webrtc_vad.is_speech(frame.tobytes(), self.sample_rate)
            except Exception:
                pass

        return self._energy_is_speech(audio_int16)

    def _energy_is_speech(self, audio_int16: np.ndarray) -> bool:
        if audio_int16.size == 0:
            return False
        rms = float(np.sqrt(np.mean(audio_int16.astype(np.float64) ** 2)))
        if rms < self.energy_threshold * 0.8:
            self._ambient_energy = self._ambient_energy * 0.95 + rms * 0.05
        threshold = max(self.energy_threshold, self._ambient_energy * 2.5)
        is_speech = rms > threshold
        if is_speech:
            self._speech_count += 1
            self._silence_count = 0
        else:
            self._silence_count += 1
            if self._silence_count > 5:
                self._speech_count = 0
        return self._speech_count >= self.min_speech_frames

    def reset(self):
        self._speech_count = 0
        self._silence_count = 0


vad = VoiceActivityDetector()
