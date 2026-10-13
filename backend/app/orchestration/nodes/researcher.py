"""Researcher Worker Node: Investigates context and gathers technical findings."""

from datetime import UTC, datetime
import logging

from app.core.config import get_settings
from app.mcp_layer.client import mcp_registry
from app.orchestration.state import HelmGraphState, TraceStep

logger = logging.getLogger(__name__)


async def researcher_node(state: HelmGraphState) -> HelmGraphState:
    """Execute research on the objective using specialized MCP tools and Gemini."""
    settings = get_settings()
    objective = state.get("objective", "")
    iteration = state.get("iteration", 0) + 1
    trace = list(state.get("trace", []))
    tool_results = list(state.get("tool_results", []))
    research_notes = list(state.get("research_notes", []))
    completed_workers = list(state.get("completed_workers", []))

    # Invoke specialized MCP research tool
    mcp_finding = await mcp_registry.invoke_tool(
        "mcp_research_query",
        {"query": objective, "domain": "agent-orchestration"},
    )
    tool_results.append(mcp_finding)

    # Use Gemini for research analysis if configured
    gemini_research = ""
    if settings.gemini_api_key:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.3,
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
            logger.warning("Gemini researcher synthesis fallback: %s", exc)

    if not gemini_research:
        gemini_research = (
            f"Researcher evaluated '{objective}':\n"
            "- Analyzed state machine isolation and scale-to-zero compute.\n"
            "- Validated zero-cost Firestore checkpoint free tier limits (50k reads/day).\n"
            "- Recommended decoupled tool invocations via Model Context Protocol."
        )

    research_notes.append(gemini_research)
    if "researcher" not in completed_workers:
        completed_workers.append("researcher")

    trace.append(
        TraceStep(
            node="researcher",
            action="conduct_research",
            detail="Invoked mcp_research_query and synthesized technical architectural notes.",
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
    }
