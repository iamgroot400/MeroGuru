from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://meroguru:change-me@localhost:5432/meroguru"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me"
    access_token_minutes: int = 15
    refresh_token_days: int = 30

    credential_encryption_key: str = "change-me"

    ai_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.1"
    ollama_embedding_model: str = "nomic-embed-text"

    youtube_api_key: str = ""
    allow_remote_models: bool = True
    telemetry_enabled: bool = False


settings = Settings()
