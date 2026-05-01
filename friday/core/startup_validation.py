import asyncio
import logging
import requests
import json
from core.service_registry import service_registry

logger = logging.getLogger(__name__)

async def validate_startup():
    """
    Verify that ollama is running and the required models are pulled.
    """
    console_logging = logging.getLogger("rich")
    
    logger.info("Starting startup validation...")
    
    # 1. Check Service Health
    await service_registry.check_all_services()
    
    if not service_registry.is_healthy("ollama"):
        logger.error("Ollama is not running. Please start Ollama before launching Friday.")
        return False

    # 2. Verify Models
    from app.core.config import settings
    required_models = ["phi3:mini", "llama3.1:8b"]
    
    try:
        resp = await asyncio.to_thread(requests.get, f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=5)
        if resp.status_code == 200:
            existing_models = [m["name"] for m in resp.json().get("models", [])]
            
            for model in required_models:
                if model not in existing_models and f"{model}:latest" not in existing_models:
                    logger.info(f"Model {model} not found. Attempting to pull...")
                    # Pulling model (this might take time)
                    pull_resp = await asyncio.to_thread(
                        requests.post, 
                        f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/pull",
                        json={"name": model},
                        timeout=600 # Long timeout for model pull
                    )
                    if pull_resp.status_code != 200:
                        logger.warning(f"Failed to pull model {model}. Limited performance expected.")
        else:
            logger.warning("Could not verify Ollama models.")
    except Exception as e:
        logger.error(f"Error during model validation: {e}")
        # We don't necessarily fail here if ollama is running, just warn
    
    logger.info("Startup validation complete.")
    return True
