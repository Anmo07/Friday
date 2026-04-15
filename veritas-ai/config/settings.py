import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(raw_value: str, default: List[str]) -> List[str]:
    if not raw_value:
        return default
    return [item.strip() for item in raw_value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_NAME: str = "Veritas AI"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    API_V1_PREFIX: str = "/api/v1"

    # Core runtime
    PIPELINE_TIMEOUT_SECONDS: int = int(os.getenv("PIPELINE_TIMEOUT_SECONDS", "45"))
    AGENT_TASK_TIMEOUT_SECONDS: int = int(os.getenv("AGENT_TASK_TIMEOUT_SECONDS", "20"))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "900"))
    CACHE_MAX_ENTRIES: int = int(os.getenv("CACHE_MAX_ENTRIES", "512"))
    HISTORY_MAX_ITEMS: int = int(os.getenv("HISTORY_MAX_ITEMS", "100"))
    ALERTS_MAX_ITEMS: int = int(os.getenv("ALERTS_MAX_ITEMS", "100"))
    ALLOW_ANONYMOUS_QUERY_ENDPOINT: bool = os.getenv("ALLOW_ANONYMOUS_QUERY_ENDPOINT", "true").lower() == "true"
    ALLOW_ANONYMOUS_WS: bool = os.getenv("ALLOW_ANONYMOUS_WS", "true").lower() == "true"

    # Public URL hints for generated links
    PUBLIC_API_BASE_URL: str = os.getenv("PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1")
    PUBLIC_WS_BASE_URL: str = os.getenv("PUBLIC_WS_BASE_URL", "ws://localhost:8000/ws/stream")

    # Ollama settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "llama3")

    # Vector DB settings
    CHROMA_PERSIST_DIRECTORY: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    # Collector API Keys
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    GNEWS_API_KEY: str = os.getenv("GNEWS_API_KEY", "")

    # Knowledge Graph Settings
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")

    # HTTP security
    CORS_ORIGINS_RAW: str = os.getenv("CORS_ORIGINS", "*")

    @property
    def cors_origins(self) -> List[str]:
        return _split_csv(self.CORS_ORIGINS_RAW, ["*"])


settings = Settings()
