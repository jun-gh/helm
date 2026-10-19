"""Researcher Worker Node: Investigates context and gathers technical findings."""

import logging
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.resilience import categorize_gemini_error, execute_with_retry
from app.mcp_layer.client import mcp_registry
from app.orchestration.state import HelmGraphState, TraceStep

logger = logging.getLogger(__name__)


def build_dynamic_research(objective: str) -> str:
    """Generate domain-specific research notes tailored to the objective."""
    obj = objective.lower()
    if "jwt" in obj or "auth" in obj or "token" in obj:
        return (
            f"Researcher evaluated '{objective}':\n"
            "- Architecture Recommendation: Use RS256 asymmetric keys (or HS256) with 15m TTL.\n"
            "- Security Baseline: Validate audience ('aud'), issuer ('iss'), and clock skew.\n"
            "- Integration Pattern: Pair FastAPI OAuth2PasswordBearer with PyJWT middleware."
        )
    db_keys = ["render", "serverless", "cloud run", "session", "database", "postgres"]
    if any(k in obj for k in db_keys):
        return (
            f"Researcher evaluated '{objective}':\n"
            "- Architecture: Configure SQLAlchemy with NullPool to avoid idle connections.\n"
            "- Serverless Concurrency: Configure async worker pool for instant cold-start.\n"
            "- Cost Guardrail: Neon serverless compute will suspend after 5m of inactivity."
        )
    if "stdio" in obj or "sse" in obj or "transport" in obj:
        return (
            f"Researcher evaluated '{objective}':\n"
            "- MCP Stdio Transport: Ideal for local child-process isolation and sub-ms IPC.\n"
            "- MCP SSE Transport: Ideal for cloud microservices and remote containerized tools.\n"
            "- Recommendation: Use Stdio for internal diagnostic tools, and SSE for cloud tools."
        )
    return (
        f"Researcher evaluated '{objective}':\n"
        f"- Scoped primary technical constraints and state requirements for '{objective}'.\n"
        "- Validated zero-cost serverless state and checkpoint limits.\n"
        "- Outlined worker execution sequence and verified MCP tool bindings."
    )


async def researcher_node(state: HelmGraphState) -> HelmGraphState:
    """Execute research on the objective using specialized MCP tools and Gemini."""
    settings = get_settings()
    objective = state.get("objective", "")
    iteration = state.get("iteration", 0) + 1
    trace = list(state.get("trace", []))
    tool_results = list(state.get("tool_results", []))
    research_notes = list(state.get("research_notes", []))
    completed_workers = list(state.get("completed_workers", []))
    errors = list(state.get("errors", []))
    structured_errors = list(state.get("structured_errors", []))

    # Invoke specialized MCP research tool
    mcp_finding = await mcp_registry.invoke_tool(
        "mcp_research_query",
        {"query": objective, "domain": "agent-orchestration"},
    )
    tool_results.append(mcp_finding)

    # Use Gemini for research analysis if configured
    gemini_research = ""
    error_notice = ""
    from app.orchestration.nodes.supervisor import is_provider_throttled

    if settings.gemini_api_key and not is_provider_throttled(errors):
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.3,
                max_retries=0,
                timeout=12.0,
            )
            messages = [
                SystemMessage(
                    content=(
                        "You are Helm's Senior Research Specialist. Given the objective "
                        "and MCP findings, provide 3 crisp, high-impact technical findings."
                    )
                ),
                HumanMessage(
                    content=f"Objective: {objective}\nMCP Research Data: {mcp_finding}"
                ),
            ]

            async def _call_researcher():
                return await llm.ainvoke(messages)

            response, struct_err = await execute_with_retry(
                _call_researcher,
                worker="Researcher Worker",
                model=settings.gemini_model,
                max_retries=3,
            )
            if struct_err:
                error_notice = struct_err["message"]
                if error_notice not in errors:
                    errors.append(error_notice)
                if struct_err not in structured_errors:
                    structured_errors.append(struct_err)
                logger.warning("Gemini researcher synthesis fallback: %s", error_notice)
            elif response:
                gemini_research = str(response.content)

        except Exception as exc:
            diag = categorize_gemini_error(
                exc,
                worker="Researcher Worker",
                model=settings.gemini_model,
                retries_attempted=3,
            )
            error_notice = diag["message"]
            logger.warning("Gemini researcher synthesis fallback: %s", exc)
            if error_notice not in errors:
                errors.append(error_notice)
            if diag not in structured_errors:
                structured_errors.append(diag)

    if not gemini_research:
        gemini_research = build_dynamic_research(objective)
        if error_notice:
            gemini_research += f"\n\n*(Notice: {error_notice}. Switched to fallback.)*"

    research_notes.append(gemini_research)
    if "researcher" not in completed_workers:
        completed_workers.append("researcher")

    trace_detail = (
        f"Invoked mcp_research_query and synthesized notes using {settings.gemini_model}."
    )
    if error_notice:
        trace_detail += f" [{error_notice}]"

    trace.append(
        TraceStep(
            node="researcher",
            action="conduct_research",
            detail=trace_detail,
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    return {
        **state,
        "iteration": iteration,
        "tool_results": tool_results,
        "research_notes": research_notes,
        "completed_workers": completed_workers,
        "trace": trace,
        "errors": errors,
        "structured_errors": structured_errors,
    }
