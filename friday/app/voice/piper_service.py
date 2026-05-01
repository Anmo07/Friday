import asyncio
import logging
import subprocess
import os
from typing import AsyncGenerator
from app.core.config import settings

logger = logging.getLogger(__name__)

class PiperTTSService:
    """
    Local-first TTS using Piper. 
    Requires 'piper' binary in PATH and a voice model (.onnx).
    """
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "models", "en_US-lessac-medium.onnx")
        self.piper_bin = "piper" # Assumed in PATH
        self._lock = asyncio.Lock()

    async def stream_audio(self, text: str) -> AsyncGenerator[bytes, None]:
        if not text:
            return
            
        if not os.path.exists(self.model_path):
            logger.warning(f"Piper model not found at {self.model_path}. Falling back to edge-tts if possible.")
            return

        async with self._lock:
            try:
                # Piper can output raw audio to stdout
                process = await asyncio.create_subprocess_exec(
                    self.piper_bin,
                    "--model", self.model_path,
                    "--output_raw",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Write text to piper's stdin
                stdout, stderr = await process.communicate(input=text.encode())
                
                if process.returncode != 0:
                    logger.error(f"Piper error: {stderr.decode()}")
                    return

                # Yield audio in chunks
                chunk_size = 4096
                for i in range(0, len(stdout), chunk_size):
                    yield stdout[i:i+chunk_size]
                    
            except Exception as e:
                logger.error(f"Piper execution failed: {e}")

piper_service = PiperTTSService()
