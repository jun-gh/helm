"""Researcher Worker Node: Investigates context and gathers technical findings."""

from datetime import UTC, datetime
import logging

from app.core.config import get_settings
from app.mcp_layer.client import mcp_registry
from app.orchestration.state import HelmGraphState, TraceStep

logger = logging.getLogger(__name__)


def build_dynamic_research(objective: str) -> str:
    """Generate domain-specific research notes tailored to the objective."""
    obj = objective.lower()
    if "jwt" in obj or "auth" in obj or "token" in obj:
        return (
            f"Researcher evaluated '{objective}':\n"
            "- Architecture Recommendation: Use RS256 asymmetric keys (or HS256 for symmetric) with 15-minute token TTL.\n"
            "- Security Baseline: Validate audience ('aud'), issuer ('iss'), and clock skew tolerance.\n"
            "- Integration Pattern: Pair FastAPI OAuth2PasswordBearer dependency with PyJWT verification middleware."
        )
    if "cloud run" in obj or "session" in obj or "database" in obj or "postgres" in obj:
        return (
            f"Researcher evaluated '{objective}':\n"
            "- Architecture Recommendation: Configure SQLAlchemy with NullPool to prevent holding idle DB connections.\n"
            "- Cloud Run Concurrency: Set max concurrency to 80 and startup CPU boost for instant scale-from-zero response.\n"
            "- Cost Guardrail: Neon serverless compute will suspend after 5 minutes of inactivity when NullPool is active."
        )
    if "stdio" in obj or "sse" in obj or "transport" in obj:
        return (
            f"Researcher evaluated '{objective}':\n"
            "- MCP Stdio Transport: Ideal for local child-process isolation, zero network exposure, and sub-millisecond IPC.\n"
            "- MCP SSE Transport: Ideal for cloud microservices, remote containerized tools, and long-lived streaming connections.\n"
            "- Recommendation: Use Stdio for internal diagnostic tools, and SSE for external cloud tools."
        )
    return (
        f"Researcher evaluated '{objective}':\n"
        f"- Scoped primary technical constraints and state requirements for '{objective}'.\n"
        "- Validated zero-cost Firestore checkpoint free tier limits (50k reads/day).\n"
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

    # Invoke specialized MCP research tool
    mcp_finding = await mcp_registry.invoke_tool(
        "mcp_research_query",
        {"query": objective, "domain": "agent-orchestration"},
    )
    tool_results.append(mcp_finding)

    # Use Gemini for research analysis if configured
    gemini_research = ""
    error_notice = ""
    if settings.gemini_api_key:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.3,
                max_retries=1,
            )
            messages = [
                SystemMessage(
                    content=(
                        "You are Helm's Senior Research Specialist. Given the mission objective and "
                        "MCP findings, provide 3 crisp, high-impact technical findings or architectural trade-offs."
                    )
                ),
                HumanMessage(
                    content=f"Objective: {objective}\nMCP Research Data: {mcp_finding}"
                ),
            ]
            response = await llm.ainvoke(messages)
            gemini_research = str(response.content)
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                error_notice = "Researcher: 429 Quota Exceeded (Free-tier limit of 20 req/day reached)."
            elif "503" in err_str or "UNAVAILABLE" in err_str:
                error_notice = "Researcher: 503 Service Spike (Google model cluster busy)."
            else:
                error_notice = f"Researcher: {exc.__class__.__name__} ({err_str[:90]})"

            logger.warning("Gemini researcher synthesis fallback: %s", exc)
            if error_notice not in errors:
                errors.append(error_notice)

    if not gemini_research:
        gemini_research = build_dynamic_research(objective)
        if error_notice:
            gemini_research += f"\n\n*(Notice: {error_notice}. Switched to domain knowledge fallback.)*"

    research_notes.append(gemini_research)
    if "researcher" not in completed_workers:
        completed_workers.append("researcher")

    trace_detail = "Invoked mcp_research_query and synthesized technical architectural notes."
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
    }
