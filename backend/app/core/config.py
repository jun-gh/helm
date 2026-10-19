"""Application settings powered by Pydantic v2 Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for Helm Backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["local", "staging", "production"] = Field(default="local")
    app_name: str = Field(default="Helm Agent Orchestrator")
    log_level: str = Field(default="INFO")
    cors_origins: str = Field(default="http://localhost:4200,https://helm.vercel.app")

    # Database: SQLite for local dev, Neon Serverless Postgres for production
    database_url: str = Field(default="sqlite+aiosqlite:///./helm_local.db")

    # Google Gemini API
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-3.8-flash")

    # Firestore State & Memory
    gcp_project_id: str = Field(default="")
    firestore_collection: str = Field(default="helm_agent_checkpoints")
    use_firestore_emulator: bool = Field(default=False)

    # Model Context Protocol (MCP)
    mcp_enabled: bool = Field(default=True)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
