"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    voyage_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"
    voyage_model: str = "voyage-3.5-lite"
    embedding_dimension: int = 1024
    log_level: str = "INFO"
    allowed_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
