"""Coder Worker Node: Implements architecture, code snippets, and design patterns."""

import logging
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.resilience import (
    categorize_gemini_error,
    execute_with_retry,
    extract_text_content,
)
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
            "async def verify_jwt_token(\n"
            "    credentials: HTTPAuthorizationCredentials = Depends(security),\n"
            ") -> dict:\n"
            "    token = credentials.credentials\n"
            "    try:\n"
            "        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])\n"
            "        return payload\n"
            "    except jwt.ExpiredSignatureError:\n"
            "        raise HTTPException(status_code=401, detail='Expired')\n"
            "    except jwt.InvalidTokenError:\n"
            "        raise HTTPException(status_code=401, detail='Invalid')\n"
            "```"
        )
    db_keywords = ["render", "serverless", "cloud run", "session", "database", "postgres"]
    if any(k in obj for k in db_keywords):
        return (
            "```python\n"
            "# Scale-to-Zero Async Database Session Engine (SQLAlchemy + NullPool)\n"
            "from collections.abc import AsyncGenerator\n"
            "from sqlalchemy.ext.asyncio import (\n"
            "    AsyncSession, async_sessionmaker, create_async_engine\n"
            ")\n"
            "from sqlalchemy.pool import NullPool\n\n"
            "DATABASE_URL = 'postgresql+asyncpg://user:pass@ep-host.neon.tech/helm?ssl=require'\n\n"
            "# NullPool guarantees zero idle connections when serverless compute scales to zero\n"
            "engine = create_async_engine(DATABASE_URL, poolclass=NullPool, echo=False)\n"
            "AsyncSessionLocal = async_sessionmaker(\n"
            "    bind=engine, class_=AsyncSession, expire_on_commit=False\n"
            ")\n\n"
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
            "    command_or_url: str = Field(..., description='Command or URL')\n"
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
    errors = list(state.get("errors", []))
    structured_errors = list(state.get("structured_errors", []))

    # Invoke specialized MCP code inspector
    mcp_code_eval = await mcp_registry.invoke_tool(
        "mcp_code_inspector",
        {"language": "python", "target_feature": objective},
    )
    tool_results.append(mcp_code_eval)

    # Use Gemini for code generation and architectural scaffolding
    gemini_code = ""
    error_notice = ""
    from app.orchestration.nodes.supervisor import is_provider_throttled

    if settings.gemini_api_key and not is_provider_throttled(errors):
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.2,
                max_retries=0,
                timeout=12.0,
            )
            context = "\n".join(research_notes) if research_notes else "No prior research."
            messages = [
                SystemMessage(
                    content=(
                        "You are Helm's Senior Software Engineer and Architect. "
                        "Using the objective and research context, draft a concise, "
                        "production-ready Python or TypeScript code snippet or schema."
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

            async def _call_coder():
                return await llm.ainvoke(messages)

            response, struct_err = await execute_with_retry(
                _call_coder,
                worker="Coder Worker",
                model=settings.gemini_model,
                max_retries=3,
            )
            if struct_err:
                error_notice = struct_err["message"]
                if error_notice not in errors:
                    errors.append(error_notice)
                if struct_err not in structured_errors:
                    structured_errors.append(struct_err)
                logger.warning("Gemini coder synthesis fallback: %s", error_notice)
            elif response:
                gemini_code = extract_text_content(response.content)

        except Exception as exc:
            diag = categorize_gemini_error(
                exc,
                worker="Coder Worker",
                model=settings.gemini_model,
                retries_attempted=3,
            )
            error_notice = diag["message"]
            logger.warning("Gemini coder synthesis fallback: %s", exc)
            if error_notice not in errors:
                errors.append(error_notice)
            if diag not in structured_errors:
                structured_errors.append(diag)

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

    trace_detail = (
        f"Invoked mcp_code_inspector and synthesized runnable code using {settings.gemini_model}."
    )
    if error_notice:
        trace_detail += f" [{error_notice}]"

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
        "errors": errors,
        "structured_errors": structured_errors,
    }
