import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Veritas AI"
    # Ollama settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # Using a common models like llama3 by default. Configurable via env var.
    MODEL_NAME: str = os.getenv("MODEL_NAME", "llama3") 

    # Vector DB settings
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    # Recommend nomic-embed-text or mxbai-embed-large for local embeddings.
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    # Collector API Keys
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    GNEWS_API_KEY: str = os.getenv("GNEWS_API_KEY", "")

    # Knowledge Graph Settings
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")

    class Config:
        env_file = ".env"

settings = Settings()
