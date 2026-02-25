from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service URLs (internal Docker network)
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    orchestrator_url: str = "http://orchestrator:8001"
    llm_adapter_url: str = "http://llm-adapter:8002"
    monitoring_url: str = "http://tool-monitoring:8003"

    # Authentication
    api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""

    # LLM Provider selection
    llm_provider: str = "groq"  # "openai" or "groq"

    # Rate limiting
    rate_limit_requests: int = 60
    rate_limit_window: int = 60  # seconds

    # Logging
    log_level: str = "INFO"

    # Audit
    audit_log_path: str = "/var/log/homelab-assistant/audit.jsonl"

    # Database
    db_path: str = "/var/lib/homelab-assistant/db.sqlite3"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
