"""API v1 router aggregating health, agents, and MCP tools endpoints."""

from fastapi import APIRouter

from app.api.endpoints import agents, health, tools

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(agents.router)
api_router.include_router(tools.router)
