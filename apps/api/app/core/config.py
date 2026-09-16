from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_base_url: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://meroguru:change-me@localhost:5432/meroguru"
    redis_url: str = "redis://localhost:6379/0"

    # Comma-separated extra origins allowed to call the API, for operators who
    # serve the frontend from something other than app_base_url.
    cors_extra_origins: str = ""

    # Per-client request ceilings. The API has no authentication by design, so
    # these are what stands between a reachable instance and unbounded use of
    # the operator's paid provider key.
    rate_limit_per_minute: int = 120
    plan_generation_rate_limit_per_hour: int = 12
    max_request_bytes: int = 1_048_576

    credential_encryption_key: str = "change-me"

    ai_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.1"
    ollama_embedding_model: str = "nomic-embed-text"

    youtube_api_key: str = ""
    allow_remote_models: bool = True
    telemetry_enabled: bool = False

    brain_base_url: str = "http://brain:8100"
    # Shared secret the API presents to the brain service. The brain performs
    # outbound requests on behalf of its caller, so it must not accept work
    # from anything that can merely reach its port.
    brain_shared_secret: str = ""


settings = Settings()


def cors_allowed_origins() -> list[str]:
    """Explicit origin allowlist. Never '*': the API has no authentication, so a
    wildcard lets any page the operator visits read and write their data."""
    origins = [settings.app_base_url.rstrip("/")]
    origins += [o.strip().rstrip("/") for o in settings.cors_extra_origins.split(",") if o.strip()]
    return list(dict.fromkeys(origins))
