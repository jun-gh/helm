"""Integration tests for health, MCP tools, and Multi-Worker LangGraph orchestration."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(autouse=True)
async def setup_database():
    """Ensure SQLite tables exist before running endpoint tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Verify /api/v1/health returns status ok and expected storage modes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database_mode"] == "sqlite-local"


@pytest.mark.asyncio
async def test_list_mcp_tools() -> None:
    """Verify /api/v1/tools returns registered built-in MCP tools."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) >= 4
    tool_names = {t["name"] for t in tools}
    assert "helm_task_planner" in tool_names
    assert "mcp_research_query" in tool_names
    assert "mcp_code_inspector" in tool_names


@pytest.mark.asyncio
async def test_run_multi_worker_orchestration() -> None:
    """Verify /api/v1/agents/run executes the Multi-Worker (Researcher + Coder) flow."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/agents/run",
            json={
                "objective": (
                    "Research serverless architecture and code a token verification module"
                ),
                "max_iterations": 2,
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["thread_id"].startswith("helm-")
    # Verify trace contains supervisor and worker handoffs
    nodes_in_trace = [step["node"] for step in payload["trace"]]
    assert "supervisor" in nodes_in_trace
    assert "researcher" in nodes_in_trace or "coder" in nodes_in_trace
    assert len(payload["trace"]) >= 3
