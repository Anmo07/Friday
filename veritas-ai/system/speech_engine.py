"""
Friday System — Speech Processing Engine (Phase 37)
=====================================================
Provides:
  1. Speech-to-Text (STT) via faster-whisper (local, GPU-optional)
  2. Text-to-Speech (TTS) via macOS native `say` + pyttsx3 fallback
  3. Streaming transcription with interrupt support

All processing is local — no cloud APIs required.
"""

import subprocess
import threading
import tempfile
import wave
import os
import time
import logging
import numpy as np
from typing import Optional, Callable

logger = logging.getLogger("friday.speech")

SAMPLE_RATE = 16000
RECORD_SECONDS = 5  # Max recording window for a single command


class SpeechToText:
    """
    Local STT using faster-whisper. Falls back to a simple
    subprocess-based whisper.cpp call if faster-whisper isn't available.
    """

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None
        self._available = False
        self._load_model()

    def _load_model(self):
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device="cpu",       # Use "cuda" if GPU available
                compute_type="int8" # Fast on CPU
            )
            self._available = True
            logger.info(f"✅ faster-whisper model [{self.model_size}] loaded.")
        except ImportError:
            logger.warning(
                "faster-whisper not installed. STT will use macOS dictation fallback.\n"
                "Install with: pip install faster-whisper"
            )
            self._available = False

    def transcribe_audio(self, audio_data: np.ndarray) -> str:
        """
        Transcribe a numpy float32 mono audio array to text.
        """
        if not self._available:
            return self._fallback_transcribe(audio_data)

        # faster-whisper expects a file path or numpy array
        segments, info = self._model.transcribe(
            audio_data,
            beam_size=3,
            language="en",
            vad_filter=True,        # Voice Activity Detection
            vad_parameters=dict(
                min_silence_duration_ms=300,
            ),
        )

        transcript = " ".join(seg.text.strip() for seg in segments)
        logger.info(f"🗣️  Transcribed: \"{transcript}\"")
        return transcript.strip()

    def _fallback_transcribe(self, audio_data: np.ndarray) -> str:
        """
        Fallback: write to temp WAV and attempt whisper CLI if installed.
        """
        try:
            tmp_path = os.path.join(tempfile.gettempdir(), "friday_stt_tmp.wav")
            self._write_wav(tmp_path, audio_data)

            result = subprocess.run(
                ["whisper", tmp_path, "--language", "en", "--model", "base", "--output_format", "txt"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                txt_path = tmp_path.replace(".wav", ".txt")
                if os.path.exists(txt_path):
                    with open(txt_path) as f:
                        return f.read().strip()
            return ""
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.error("No STT backend available. Install faster-whisper or whisper CLI.")
            return ""

    @staticmethod
    def _write_wav(path: str, audio: np.ndarray):
        """Write float32 mono audio to a 16-bit WAV file."""
        int_audio = (audio * 32767).astype(np.int16)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(int_audio.tobytes())


class TextToSpeech:
    """
    Local TTS engine. Prefers macOS native `say` for lowest latency
    and highest quality. Falls back to pyttsx3 cross-platform.
    """

    def __init__(self, voice: str = "Samantha", rate: int = 190):
        self.voice = voice
        self.rate = rate
        self._speaking = False
        self._process: Optional[subprocess.Popen] = None
        self._platform = self._detect_platform()

    @staticmethod
    def _detect_platform() -> str:
        import platform
        return platform.system().lower()

    def speak(self, text: str):
        """
        Speak the given text. Non-blocking — runs in a background thread.
        """
        if not text.strip():
            return

        # Interrupt any current speech
        self.interrupt()

        self._speaking = True
        thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
        thread.start()

    def _speak_sync(self, text: str):
        """Synchronous speech — called from background thread."""
        try:
            if self._platform == "darwin":
                self._speak_macos(text)
            else:
                self._speak_pyttsx3(text)
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            self._speaking = False

    def _speak_macos(self, text: str):
        """Use macOS native `say` command — ultra low latency, high quality."""
        self._process = subprocess.Popen(
            ["say", "-v", self.voice, "-r", str(self.rate), text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._process.wait()

    def _speak_pyttsx3(self, text: str):
        """Cross-platform fallback using pyttsx3."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.say(text)
            engine.runAndWait()
        except ImportError:
            logger.error("pyttsx3 not installed. Run: pip install pyttsx3")

    def interrupt(self):
        """Immediately stop any ongoing speech."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            logger.debug("Speech interrupted.")
        self._speaking = False

    @property
    def is_speaking(self) -> bool:
        return self._speaking


class VoiceCommandCapture:
    """
    Records a fixed-duration audio clip from the microphone after activation,
    then passes it to STT for transcription.
    """

    def __init__(self, stt: SpeechToText, duration: float = RECORD_SECONDS):
        self.stt = stt
        self.duration = duration

    def capture_and_transcribe(self) -> str:
        """
        Record from microphone for `self.duration` seconds, then transcribe.
        Returns the transcription text.
        """
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed.")
            return ""

        logger.info(f"🎤 Recording for {self.duration}s...")
        audio = sd.rec(
            int(self.duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()  # Block until recording completes
        audio = audio.flatten()
        logger.info("Recording complete. Transcribing...")

        return self.stt.transcribe_audio(audio)


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    tts = TextToSpeech()
    tts.speak("Friday online. Awaiting your command.")

    stt = SpeechToText(model_size="base")
    capture = VoiceCommandCapture(stt, duration=4)

    time.sleep(2)  # Wait for TTS to finish

    print("Speak now...")
    text = capture.capture_and_transcribe()
    print(f"You said: {text}")

    tts.speak(f"I heard: {text}")
    time.sleep(3)
