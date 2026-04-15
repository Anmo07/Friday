from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
from langchain_community.llms import Ollama

from config.settings import settings

# Phase 9: Assign a persistent identical-query cache across all Agent logic mapping LLMs
set_llm_cache(SQLiteCache(database_path=".veritas_llm_cache.db"))

def get_llm() -> Ollama:
    """
    Initialize and return the base LLM for Veritas AI agents.
    Defaulting to Ollama pointing to local Ollama instance.
    """
    return Ollama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.MODEL_NAME,
        temperature=0.0
    )
