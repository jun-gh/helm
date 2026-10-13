"""Coder Worker Node: Implements architecture, code snippets, and design patterns."""

from datetime import UTC, datetime
import logging

from app.core.config import get_settings
from app.mcp_layer.client import mcp_registry
from app.orchestration.state import HelmGraphState, TraceStep

logger = logging.getLogger(__name__)


def build_dynamic_code(objective: str) -> str:
    """Generate domain-specific code snippets tailored to the objective."""
    obj = objective.lower()
    if "jwt" in obj or "auth" in obj or "token" in obj:
        return (
            "```python\n"
            "# Production-Grade JWT Token Validator (FastAPI + PyJWT)\n"
            "from fastapi import Depends, HTTPException, status\n"
            "from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials\n"
            "import jwt\n\n"
            "security = HTTPBearer()\n"
            "JWT_SECRET = 'your-secret-key'\n"
            "ALGORITHM = 'HS256'\n\n"
            "async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:\n"
            "    token = credentials.credentials\n"
            "    try:\n"
            "        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])\n"
            "        return payload\n"
            "    except jwt.ExpiredSignatureError:\n"
            "        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token expired')\n"
            "    except jwt.InvalidTokenError:\n"
            "        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')\n"
            "```"
        )
    if "cloud run" in obj or "session" in obj or "database" in obj or "postgres" in obj:
        return (
            "```python\n"
            "# Scale-to-Zero Async Database Session Engine (SQLAlchemy + NullPool)\n"
            "from collections.abc import AsyncGenerator\n"
            "from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine\n"
            "from sqlalchemy.pool import NullPool\n\n"
            "DATABASE_URL = 'postgresql+asyncpg://user:pass@ep-host.neon.tech/helm?ssl=require'\n\n"
            "# NullPool guarantees zero idle connections when Cloud Run scales to zero\n"
            "engine = create_async_engine(DATABASE_URL, poolclass=NullPool, echo=False)\n"
            "AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)\n\n"
            "async def get_db_session() -> AsyncGenerator[AsyncSession, None]:\n"
            "    async with AsyncSessionLocal() as session:\n"
            "        yield session\n"
            "```"
        )
    if "stdio" in obj or "sse" in obj or "transport" in obj:
        return (
            "```python\n"
            "# MCP Dual-Transport Configuration Manager\n"
            "from typing import Literal\n"
            "from pydantic import BaseModel, Field\n\n"
            "class MCPTransportConfig(BaseModel):\n"
            "    server_name: str\n"
            "    transport_type: Literal['stdio', 'sse']\n"
            "    command_or_url: str = Field(..., description='Shell command for stdio, or HTTP endpoint for SSE')\n"
            "    timeout_seconds: float = 30.0\n"
            "    headers: dict[str, str] = Field(default_factory=dict)\n"
            "```"
        )
    return (
        "```python\n"
        "# Helm Domain Architecture Scaffold\n"
        "from pydantic import BaseModel, Field\n\n"
        "class OrchestrationTask(BaseModel):\n"
        f"    name: str = '{objective}'\n"
        "    scale_to_zero_ready: bool = True\n"
        "    mcp_bindings: list[str] = ['helm_task_planner', 'helm_cluster_telemetry']\n"
        "```"
    )


async def coder_node(state: HelmGraphState) -> HelmGraphState:
    """Design and implement technical code solutions using specialized MCP tools and Gemini."""
    settings = get_settings()
    objective = state.get("objective", "")
    iteration = state.get("iteration", 0) + 1
    trace = list(state.get("trace", []))
    tool_results = list(state.get("tool_results", []))
    code_artifacts = list(state.get("code_artifacts", []))
    research_notes = state.get("research_notes", [])
    completed_workers = list(state.get("completed_workers", []))

    # Invoke specialized MCP code inspector
    mcp_code_eval = await mcp_registry.invoke_tool(
        "mcp_code_inspector",
        {"language": "python", "target_feature": objective},
    )
    tool_results.append(mcp_code_eval)

    # Use Gemini for code generation and architectural scaffolding
    gemini_code = ""
    error_notice = ""
    if settings.gemini_api_key:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.2,
            )
            context = "\n".join(research_notes) if research_notes else "No prior research."
            messages = [
                SystemMessage(
                    content=(
                        "You are Helm's Senior Software Engineer and Architect. "
                        "Using the objective and research context, draft a concise, production-ready "
                        "Python or TypeScript code snippet or structural schema that solves the objective."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Objective: {objective}\n"
                        f"Research Context:\n{context}\n"
                        f"MCP Code Inspector:\n{mcp_code_eval}"
                    )
                ),
            ]
            response = await llm.ainvoke(messages)
            gemini_code = str(response.content)
        except Exception as exc:
            error_notice = f"Gemini error ({exc.__class__.__name__}: {str(exc)[:90]})"
            logger.warning("Gemini coder synthesis fallback: %s", exc)

    if not gemini_code:
        gemini_code = build_dynamic_code(objective)

    code_artifacts.append(
        {
            "objective": objective,
            "snippet": gemini_code,
            "inspector_verdict": mcp_code_eval.get("serverless_readiness", "Ready"),
        }
    )
    if "coder" not in completed_workers:
        completed_workers.append("coder")

    trace_detail = "Invoked mcp_code_inspector and synthesized runnable code scaffolding."
    if error_notice:
        trace_detail += f" ({error_notice})"

    trace.append(
        TraceStep(
            node="coder",
            action="implement_code",
            detail=trace_detail,
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    return {
        **state,
        "iteration": iteration,
        "tool_results": tool_results,
        "code_artifacts": code_artifacts,
        "completed_workers": completed_workers,
        "trace": trace,
    }
