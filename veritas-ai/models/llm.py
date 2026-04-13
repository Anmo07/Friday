from langchain_ollama import ChatOllama
from config.settings import settings

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
