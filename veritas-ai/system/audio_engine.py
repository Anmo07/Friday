"""
Friday System — Audio Activation Engine (Phase 36)
===================================================
Continuous microphone listener with two activation triggers:
  1. Double-clap detection via energy spike pattern matching
  2. Wake word "Friday" via keyword spotting

This module runs as an independent async loop and emits activation
events that downstream agents (Phase 39) consume.
"""

import numpy as np
import threading
import time
import logging
import asyncio
from typing import Callable, Optional

logger = logging.getLogger("friday.audio_engine")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SAMPLE_RATE = 16000         # 16 kHz — standard for speech models
BLOCK_SIZE = 1024           # ~64ms per block at 16 kHz
CLAP_ENERGY_THRESHOLD = 0.35  # RMS energy above this = "spike"
CLAP_MAX_GAP_SEC = 0.6     # Max seconds between two claps
CLAP_MIN_GAP_SEC = 0.08    # Min seconds between two claps (debounce)
COOLDOWN_SEC = 2.0          # Seconds before listening for next activation


class ClapDetector:
    """
    Detects a double-clap pattern by analyzing RMS energy spikes
    in short audio frames. Two spikes within the gap window trigger activation.
    """

    def __init__(self, threshold: float = CLAP_ENERGY_THRESHOLD,
                 min_gap: float = CLAP_MIN_GAP_SEC,
                 max_gap: float = CLAP_MAX_GAP_SEC):
        self.threshold = threshold
        self.min_gap = min_gap
        self.max_gap = max_gap
        self._last_spike_time: Optional[float] = None

    def feed(self, audio_block: np.ndarray) -> bool:
        """
        Feed an audio block (float32, mono).
        Returns True if a double-clap was detected.
        """
        rms = np.sqrt(np.mean(audio_block ** 2))

        if rms >= self.threshold:
            now = time.monotonic()
            if self._last_spike_time is not None:
                gap = now - self._last_spike_time
                if self.min_gap <= gap <= self.max_gap:
                    self._last_spike_time = None  # Reset for next detection
                    return True
            self._last_spike_time = now

        return False

    def reset(self):
        self._last_spike_time = None


class WakeWordDetector:
    """
    Lightweight wake-word detector stub.
    
    In production, replace the `detect()` method body with:
      - Porcupine (pvporcupine) for ultra-low-latency keyword spotting
      - Vosk for offline keyword detection
      - OR a tiny ONNX classifier trained on "Friday"
    
    For the MVP, this uses energy-gated silence detection to simulate
    wake-word boundaries. The actual transcription check happens in the
    STT module (Phase 37) which validates if the spoken word is "Friday".
    """

    def __init__(self, keyword: str = "friday"):
        self.keyword = keyword.lower()
        self._speech_frames = 0
        self._silence_frames = 0
        self._SPEECH_THRESHOLD = 0.04  # RMS above this = speech
        self._MIN_SPEECH_FRAMES = 8    # ~500ms of speech
        self._MAX_SPEECH_FRAMES = 30   # ~2s cap

    def feed(self, audio_block: np.ndarray) -> bool:
        """
        Feed audio block. Returns True when a short speech burst is detected
        (potential wake word). The STT pipeline then validates the content.
        """
        rms = np.sqrt(np.mean(audio_block ** 2))

        if rms >= self._SPEECH_THRESHOLD:
            self._speech_frames += 1
            self._silence_frames = 0
        else:
            if self._speech_frames >= self._MIN_SPEECH_FRAMES:
                self._silence_frames += 1
                # Speech burst ended — potential wake word
                if self._silence_frames >= 4:
                    self._speech_frames = 0
                    self._silence_frames = 0
                    return True
            else:
                self._speech_frames = 0
                self._silence_frames = 0

        # Safety cap: don't buffer forever
        if self._speech_frames > self._MAX_SPEECH_FRAMES:
            self._speech_frames = 0
            return True

        return False

    def reset(self):
        self._speech_frames = 0
        self._silence_frames = 0


class AudioActivationEngine:
    """
    The main engine that runs continuous microphone capture in a background
    thread and dispatches activation events when double-clap or wake-word
    is detected.

    Usage:
        engine = AudioActivationEngine(on_activate=my_callback)
        engine.start()
        ...
        engine.stop()
    """

    def __init__(self, on_activate: Optional[Callable] = None,
                 enable_clap: bool = True,
                 enable_wake_word: bool = True):
        self.on_activate = on_activate
        self.enable_clap = enable_clap
        self.enable_wake_word = enable_wake_word

        self._clap_detector = ClapDetector()
        self._wake_detector = WakeWordDetector()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cooldown_until = 0.0

    def start(self):
        """Start the background audio capture thread."""
        if self._running:
            logger.warning("Audio engine already running.")
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("🎙️  Friday Audio Activation Engine started. Listening...")

    def stop(self):
        """Gracefully stop the audio capture thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        logger.info("🔇  Friday Audio Activation Engine stopped.")

    def _capture_loop(self):
        """
        Core capture loop. Runs in a dedicated thread to avoid blocking
        the main asyncio event loop.
        """
        try:
            import sounddevice as sd
        except ImportError:
            logger.error(
                "sounddevice not installed. Run: pip install sounddevice\n"
                "Audio activation disabled."
            )
            self._running = False
            return

        def _audio_callback(indata, frames, time_info, status):
            if status:
                logger.debug(f"Audio stream status: {status}")

            if not self._running:
                return

            # Cooldown period after activation
            if time.monotonic() < self._cooldown_until:
                return

            # Convert to mono float32
            audio = indata[:, 0].astype(np.float32)

            activated = False
            trigger_source = ""

            # Check double-clap
            if self.enable_clap and self._clap_detector.feed(audio):
                activated = True
                trigger_source = "double_clap"

            # Check wake word boundary
            if not activated and self.enable_wake_word and self._wake_detector.feed(audio):
                activated = True
                trigger_source = "wake_word_boundary"

            if activated:
                self._cooldown_until = time.monotonic() + COOLDOWN_SEC
                self._clap_detector.reset()
                self._wake_detector.reset()
                logger.info(f"✅ ACTIVATION DETECTED via [{trigger_source}]")

                if self.on_activate:
                    try:
                        self.on_activate(trigger_source)
                    except Exception as e:
                        logger.error(f"Activation callback error: {e}")

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                channels=1,
                dtype="float32",
                callback=_audio_callback,
            ):
                while self._running:
                    time.sleep(0.1)  # Keep thread alive, callback does the work
        except Exception as e:
            logger.error(f"Audio stream failed: {e}")
            self._running = False


# ---------------------------------------------------------------------------
# Standalone test / demo
# ---------------------------------------------------------------------------

def _demo_activation(trigger: str):
    print(f"\n🚀  FRIDAY ACTIVATED! Trigger: {trigger}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = AudioActivationEngine(on_activate=_demo_activation)
    engine.start()

    try:
        print("Listening for double-clap or wake word... (Ctrl+C to stop)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        engine.stop()
        print("Stopped.")
