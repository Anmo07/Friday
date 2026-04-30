import asyncio
import tempfile
from pathlib import Path
import edge_tts

# Common profiles for the TTS engine
VOICE_PROFILES = {
    "friday": "en-US-JennyNeural",
    "jarvis": "en-GB-RyanNeural"
}

class TTSEngine:
    def __init__(self, voice_id: str = "friday"):
        self.voice = VOICE_PROFILES.get(voice_id, "en-US-JennyNeural")
    
    async def generate_speech(self, text: str) -> bytes:
        """Generates speech via edge-tts and returns the raw mp3 bytes."""
        communicate = edge_tts.Communicate(text, self.voice)
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            temp_path = tmp.name
        
        await communicate.save(temp_path)
        
        audio_data = Path(temp_path).read_bytes()
        Path(temp_path).unlink(missing_ok=True)
        return audio_data

tts_engine = TTSEngine()
