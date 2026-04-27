"""Application configuration via pydantic-settings.

Migrated from config/settings.py. All env vars and defaults are preserved.
"""
from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(raw_value: str, default: List[str]) -> List[str]:
    """Split a comma-separated string into a list, returning *default* when empty."""
    if not raw_value:
        return default
    return [item.strip() for item in raw_value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Central application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "Veritas AI"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # ── Core runtime ─────────────────────────────────────────────
    PIPELINE_TIMEOUT_SECONDS: int = 300
    AGENT_TASK_TIMEOUT_SECONDS: int = 120
    CACHE_TTL_SECONDS: int = 900
    CACHE_MAX_ENTRIES: int = 512
    HISTORY_MAX_ITEMS: int = 100
    ALERTS_MAX_ITEMS: int = 100
    ALLOW_ANONYMOUS_QUERY_ENDPOINT: bool = True
    ALLOW_ANONYMOUS_WS: bool = True

    # ── Public URL hints ─────────────────────────────────────────
    PUBLIC_API_BASE_URL: str = "http://localhost:8001/api/v1"
    PUBLIC_WS_BASE_URL: str = "ws://localhost:8001/ws/stream"

    # ── Ollama / LLM ─────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_NAME: str = "llama3"
    ROUTER_MODEL: str = "phi3"
    FAST_MODEL: str = "mistral"
    OLLAMA_REQUEST_TIMEOUT_SECONDS: int = 120
    LOCAL_LLM_PROFILE: str = "balanced"

    # ── Voice (local speech pipeline) ────────────────────────────
    STT_MODEL_SIZE: str = "base"
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"
    TTS_PROVIDER: str = "pyttsx3"  # pyttsx3 | edge_tts
    TTS_VOICE_PROFILE: str = "friday"
    TTS_SPEECH_RATE: int = 190

    # ── Autonomy safety policy ────────────────────────────────────
    CONTROL_CONFIRMATION_POLICY: str = "confirm_high_risk"
    CONTROL_AUDIT_LOG_PATH: str = "./logs/control_audit.log"
    CONTROL_ALLOW_FULL_AUTO: bool = False

    # ── Internet-aware retrieval ──────────────────────────────────
    WEB_ENRICHMENT_ENABLED: bool = True
    WEB_ENRICHMENT_TIMEOUT_SECONDS: int = 4
    WEB_ENRICHMENT_MAX_RESULTS: int = 3

    # ── Vector DB ────────────────────────────────────────────────
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    RETRIEVAL_K: int = 3

    # ── Redis ────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # ── Collector API keys ───────────────────────────────────────
    NEWS_API_KEY: str = ""
    GNEWS_API_KEY: str = ""

    # ── Knowledge Graph ──────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ── HTTP security ────────────────────────────────────────────
    CORS_ORIGINS_RAW: str = "*"

    # ── Performance ──────────────────────────────────────────────
    MAX_PARALLEL_TOOLS: int = 3
    ENABLE_STREAMING: bool = True
    STREAM_CHUNK_SIZE: int = 100

    # ── Derived helpers ──────────────────────────────────────────
    @property
    def cors_origins(self) -> List[str]:
        return _split_csv(self.CORS_ORIGINS_RAW, ["*"])

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()
