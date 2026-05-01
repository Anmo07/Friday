from __future__ import annotations
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(raw_value: str, default: List[str]) -> List[str]:
    if not raw_value:
        return default
    return [item.strip() for item in raw_value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    APP_NAME: str = "Friday"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    PIPELINE_TIMEOUT_SECONDS: int = 300
    AGENT_TASK_TIMEOUT_SECONDS: int = 120
    CACHE_TTL_SECONDS: int = 900
    CACHE_MAX_ENTRIES: int = 512
    HISTORY_MAX_ITEMS: int = 100
    ALERTS_MAX_ITEMS: int = 100
    ALLOW_ANONYMOUS_QUERY_ENDPOINT: bool = True
    ALLOW_ANONYMOUS_WS: bool = True
    PUBLIC_API_BASE_URL: str = "http://localhost:8001/api/v1"
    PUBLIC_WS_BASE_URL: str = "ws://localhost:8001/ws/stream"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_NAME: str = "llama3"
    ROUTER_MODEL: str = "phi3"
    FAST_MODEL: str = "mistral"
    OLLAMA_REQUEST_TIMEOUT_SECONDS: int = 120
    LOCAL_LLM_PROFILE: str = "balanced"
    STT_MODEL_SIZE: str = "base"
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"
    TTS_PROVIDER: str = "edge-tts"
    TTS_VOICE_PROFILE: str = "en-US-JennyNeural"
    TTS_SPEECH_RATE: int = 190
    CONTROL_CONFIRMATION_POLICY: str = "confirm_high_risk"
    CONTROL_AUDIT_LOG_PATH: str = "./logs/control_audit.log"
    CONTROL_ALLOW_FULL_AUTO: bool = False
    WEB_ENRICHMENT_ENABLED: bool = True
    WEB_ENRICHMENT_TIMEOUT_SECONDS: int = 4
    WEB_ENRICHMENT_MAX_RESULTS: int = 3
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    RETRIEVAL_K: int = 3
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    NEWS_API_KEY: str = ""
    GNEWS_API_KEY: str = ""
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    CORS_ORIGINS_RAW: str = "*"
    MAX_PARALLEL_TOOLS: int = 3
    ENABLE_STREAMING: bool = True
    STREAM_CHUNK_SIZE: int = 100

    @property
    def cors_origins(self) -> List[str]:
        return _split_csv(self.CORS_ORIGINS_RAW, ["*"])

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()
