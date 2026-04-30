from __future__ import annotations
import asyncio
import logging
from functools import lru_cache
from typing import Any, Iterable, Optional
import requests
from langchain_core.language_models.llms import LLM
from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaModelUnavailableError(RuntimeError):
    pass


class OllamaLLM(LLM):
    base_url: str = settings.OLLAMA_BASE_URL
    model: str
    temperature: float = 0.0
    timeout: int = settings.OLLAMA_REQUEST_TIMEOUT_SECONDS

    @property
    def _llm_type(self) -> str:
        return "ollama_http"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "timeout": self.timeout,
        }

    def _call(
        self,
        prompt: str,
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }
        response = requests.post(
            f"{self.base_url.rstrip('/')}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        if stop:
            for token in stop:
                if token and token in text:
                    text = text.split(token, 1)[0]
                    break
        return text

    async def _acall(
        self,
        prompt: str,
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> str:
        return await asyncio.to_thread(self._call, prompt, stop, run_manager, **kwargs)


def _normalize_model_name(name: str) -> str:
    return name.strip().lower().split(":", 1)[0]


@lru_cache(maxsize=4)
def list_installed_models(base_url: str = settings.OLLAMA_BASE_URL) -> tuple[str, ...]:
    endpoint = f"{base_url.rstrip('/')}/api/tags"
    try:
        response = requests.get(endpoint, timeout=2)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.info("Ollama tags unavailable at %s: %s", endpoint, exc)
        return ()
    models = payload.get("models", [])
    names = [item.get("name", "").strip() for item in models if item.get("name")]
    return tuple(names)


def refresh_installed_models(
    base_url: str = settings.OLLAMA_BASE_URL,
) -> tuple[str, ...]:
    list_installed_models.cache_clear()
    return list_installed_models(base_url)


def resolve_model_name(
    preferred_models: Iterable[str],
    *,
    base_url: str = settings.OLLAMA_BASE_URL,
) -> Optional[str]:
    installed = list_installed_models(base_url)
    if not installed:
        return None
    by_exact = {name.lower(): name for name in installed}
    by_base = {_normalize_model_name(name): name for name in installed}
    for candidate in preferred_models:
        if not candidate:
            continue
        lowered = candidate.strip().lower()
        if lowered in by_exact:
            return by_exact[lowered]
        normalized = _normalize_model_name(candidate)
        if normalized in by_base:
            return by_base[normalized]
    return installed[0]


def create_ollama_llm(
    *,
    model: str,
    temperature: float = 0.0,
    callbacks: Optional[list[Any]] = None,
    base_url: str = settings.OLLAMA_BASE_URL,
    timeout: int = 120,
) -> OllamaLLM:
    kwargs: dict[str, Any] = {
        "base_url": base_url,
        "model": model,
        "temperature": temperature,
        "timeout": timeout,
    }
    if callbacks:
        kwargs["callbacks"] = callbacks
    return OllamaLLM(**kwargs)


def require_model_name(
    preferred_models: Iterable[str],
    *,
    base_url: str = settings.OLLAMA_BASE_URL,
) -> str:
    model = resolve_model_name(preferred_models, base_url=base_url)
    if model:
        return model
    raise OllamaModelUnavailableError(
        "No local Ollama models are installed. Pull one with `ollama pull <model>` "
        "or set MODEL_NAME / FAST_MODEL to a model that exists locally."
    )
