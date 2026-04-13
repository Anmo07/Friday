import os
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from config.settings import settings

def get_embeddings() -> OllamaEmbeddings:
    """Return local Ollama embeddings wrapper."""
    return OllamaEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )

def get_vector_store() -> Chroma:
    """
    Initialize and return the Chroma Vector Store.
    This creates a local persistent database if it doesn't already exist.
    """
    os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    embeddings = get_embeddings()
    return Chroma(
        collection_name="veritas_knowledge_base",
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIRECTORY
    )
