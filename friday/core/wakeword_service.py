import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

class WakeWordService:
    """
    Handles hands-free activation. 
    In production, this would use openwakeword or Porcupine for sub-50ms local detection.
    For now, it provides a consistent interface and a placeholder for 'Hey Friday'.
    """
    def __init__(self, model_name: str = "hey_friday"):
        self.model_name = model_name
        self._enabled = True
        self._is_active = False

    async def detect(self, audio_data: bytes) -> bool:
        """
        Stub for wake word detection. 
        Returns True if 'Hey Friday' is detected.
        """
        if not self._enabled:
            return False
            
        # Placeholder for real model inference
        # To integrate openwakeword:
        # 1. pip install openwakeword
        # 2. oww_model = Model(wakeword_models=["hey_friday"])
        # 3. return oww_model.predict(audio_data)
        
        return False

    def enable(self):
        self._enabled = True
        
    def disable(self):
        self._enabled = False

wakeword_service = WakeWordService()
