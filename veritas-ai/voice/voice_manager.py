import asyncio
import io

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from voice.tts_engine import tts_engine

class VoiceManager:
    def __init__(self, model_size="tiny", device="cpu", compute_type="int8"):
        if WhisperModel:
            # Initialize with small model for fast latency
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        else:
            self.model = None
            print("Warning: faster_whisper not installed. STT disabled.")

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribe incoming audio bytes using Faster Whisper (run in thread)."""
        if not self.model:
            return ""

        def _transcribe():
            # In a real setup, we'd ensure audio_bytes is properly formatted (e.g. WAV).
            # faster_whisper can accept an IO object if it's a valid audio format.
            try:
                segments, _ = self.model.transcribe(io.BytesIO(audio_bytes), beam_size=5)
                return " ".join([segment.text for segment in segments]).strip()
            except Exception as e:
                print(f"Transcription error: {e}")
                return ""
            
        return await asyncio.to_thread(_transcribe)

voice_manager = VoiceManager()
