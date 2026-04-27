from typing import Any, Dict, List
import time
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
from langchain_core.callbacks.base import BaseCallbackHandler

from config.settings import settings
from core.observability import observability
from models.ollama_runtime import (
    OllamaLLM,
    create_ollama_llm,
    require_model_name,
)

class ObservabilityCallbackHandler(BaseCallbackHandler):
    """
    Tracks inference metrics (latency, token usage, confidence) 
    and sends them to the global ObservabilityLayer.
    """
    def __init__(self):
        self.start_times = {}

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        run_id = kwargs.get("run_id")
        self.start_times[run_id] = time.time()
        import logging
        logging.getLogger(__name__).info(f"LLM request start: {run_id}")

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        run_id = kwargs.get("run_id")
        import logging
        logging.getLogger(__name__).info(f"LLM request end: {run_id}")
        end_time = time.time()
        start_time = self.start_times.pop(run_id, end_time)
        latency = end_time - start_time
        
        # Depending on provider, extraction varies. Setting up flexible logic constraint.
        llm_output = response.llm_output or {}
        token_usage = llm_output.get("token_usage", {})
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        
        confidence = None
        if hasattr(response, "generations") and len(response.generations) > 0 and len(response.generations[0]) > 0:
            gen_info = response.generations[0][0].generation_info or {}
            confidence = gen_info.get("confidence")

        observability.log_llm_metrics(
            latency=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            confidence=confidence
        )

# Phase 9: Assign a persistent identical-query cache across all Agent logic mapping LLMs
set_llm_cache(SQLiteCache(database_path=".veritas_llm_cache.db"))

def get_llm() -> OllamaLLM:
    """
    Initialize and return the base LLM for Veritas AI agents.
    Defaulting to Ollama pointing to local Ollama instance.
    """
    return create_ollama_llm(
        model=require_model_name(
            [settings.MODEL_NAME, settings.FAST_MODEL, settings.ROUTER_MODEL],
            base_url=settings.OLLAMA_BASE_URL,
        ),
        temperature=0.0,
        callbacks=[ObservabilityCallbackHandler()],
        base_url=settings.OLLAMA_BASE_URL,
    )
