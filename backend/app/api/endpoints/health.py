"""Health and readiness probe endpoints for Render, containerized, and local development."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.memory.sql_store import state_store

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """System health and active storage telemetry."""

    status: str
    service: str
    environment: str
    database_mode: str
    state_store_mode: str
    gemini_configured: bool
    gemini_model: str
    mcp_enabled: bool


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Return liveness status and active storage/AI configuration."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        database_mode="neon-postgres" if settings.is_postgres else "sqlite-local",
        state_store_mode=state_store.backend_mode,
        gemini_configured=bool(settings.gemini_api_key),
        gemini_model=settings.gemini_model,
        mcp_enabled=settings.mcp_enabled,
    )
