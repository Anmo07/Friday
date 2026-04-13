from langchain_ollama import ChatOllama
from config.settings import settings
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

# Phase 9: Assign a persistent identical-query cache across all Agent logic mapping LLMs
set_llm_cache(SQLiteCache(database_path=".veritas_llm_cache.db"))

def get_llm() -> ChatOllama:
    """
    Initialize and return the base LLM for Veritas AI agents.
    Defaulting to ChatOllama pointing to local Ollama instance.
    We set format='json' to encourage models to output structured data.
    """
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.MODEL_NAME,
        temperature=0.0,
        format="json"
    )
