import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_community.llms import Ollama
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

from config.settings import settings
from core.observability import observability


class ModelTier(Enum):
    FAST = "fast"
    MEDIUM = "medium"
    HEAVY = "heavy"


@dataclass
class ModelConfig:
    name: str
    tier: ModelTier
    temperature: float = 0.0
    timeout: int = 120


LLM_CONFIGS = {
    ModelTier.FAST: ModelConfig(
        name=settings.FAST_MODEL or "phi3",
        tier=ModelTier.FAST,
        temperature=0.0,
        timeout=60,
    ),
    ModelTier.MEDIUM: ModelConfig(
        name=settings.MODEL_NAME or "mistral",
        tier=ModelTier.MEDIUM,
        temperature=0.0,
        timeout=120,
    ),
    ModelTier.HEAVY: ModelConfig(
        name=settings.MODEL_NAME or "llama3",
        tier=ModelTier.HEAVY,
        temperature=0.0,
        timeout=180,
    ),
}


class MetricsCallbackHandler(BaseCallbackHandler):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.start_times: Dict[str, float] = {}

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> Any:
        run_id = str(id(kwargs.get("run_id", id(prompts))))
        self.start_times[run_id] = time.time()

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        run_id = str(id(kwargs.get("run_id")))
        end_time = time.time()
        start_time = self.start_times.pop(run_id, end_time)
        latency = end_time - start_time

        llm_output = response.llm_output or {}
        token_usage = llm_output.get("token_usage", {})
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)

        observability.log_llm_metrics(
            latency=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            confidence=None,
        )


class LLMManager:
    _instance: Optional["LLMManager"] = None
    _llms: Dict[ModelTier, Ollama] = {}
    _lock_initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_llm(self, tier: ModelTier = ModelTier.MEDIUM) -> Ollama:
        if tier not in self._llms:
            config = LLM_CONFIGS.get(tier, LLM_CONFIGS[ModelTier.MEDIUM])
            self._llms[tier] = Ollama(
                base_url=settings.OLLAMA_BASE_URL,
                model=config.name,
                temperature=config.temperature,
                callbacks=[MetricsCallbackHandler(config.name)],
            )
        return self._llms[tier]

    def get_fast_llm(self) -> Ollama:
        return self.get_llm(ModelTier.FAST)

    def get_medium_llm(self) -> Ollama:
        return self.get_llm(ModelTier.MEDIUM)

    def get_heavy_llm(self) -> Ollama:
        return self.get_llm(ModelTier.HEAVY)

    async def preload_models(self) -> List[str]:
        loaded_models = []
        for tier in [ModelTier.FAST, ModelTier.MEDIUM]:
            try:
                llm = self.get_llm(tier)
                config = LLM_CONFIGS[tier]
                result = llm.invoke("Hello")
                loaded_models.append(config.name)
            except Exception as e:
                print(f"Warning: Could not preload {tier.value} model: {e}")
        return loaded_models

    def get_available_models(self) -> List[str]:
        return [config.name for config in LLM_CONFIGS.values()]


set_llm_cache(SQLiteCache(database_path=".veritas_llm_cache.db"))


llm_manager = LLMManager()


def get_llm(tier: ModelTier = ModelTier.MEDIUM) -> Ollama:
    return llm_manager.get_llm(tier)


def get_fast_llm() -> Ollama:
    return llm_manager.get_fast_llm()


def get_heavy_llm() -> Ollama:
    return llm_manager.get_heavy_llm()
