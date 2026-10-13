"""Supervisor Node: Steers execution using Google Gemini or deterministic fallback."""

from datetime import UTC, datetime
import logging

from app.core.config import get_settings
from app.orchestration.state import HelmGraphState, TraceStep

logger = logging.getLogger(__name__)


async def supervisor_node(state: HelmGraphState) -> HelmGraphState:
    """Coordinate worker execution and synthesize the final mission report."""
    settings = get_settings()
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 1)
    trace = list(state.get("trace", []))
    objective = state.get("objective", "")

    if iteration < max_iterations:
        trace.append(
            TraceStep(
                node="supervisor",
                action="delegate_to_worker",
                detail=f"Steering objective to MCP worker (pass {iteration + 1}/{max_iterations}).",
                timestamp=datetime.now(UTC).isoformat(),
            )
        )
        return {
            **state,
            "next_agent": "worker",
            "trace": trace,
        }

    # Synthesize final output using Google Gemini if GEMINI_API_KEY is configured
    tool_results = state.get("tool_results", [])
    final_response = ""

    if settings.gemini_api_key:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.2,
            )
            messages = [
                SystemMessage(
                    content=(
                        "You are Helm, an AI Agent Orchestrator. Summarize the mission results "
                        "concisely based on the worker's MCP tool outputs."
                    )
                ),
                HumanMessage(
                    content=f"Objective: {objective}\nWorker MCP Telemetry: {tool_results}"
                ),
            ]
            ai_msg = await llm.ainvoke(messages)
            final_response = str(ai_msg.content)
        except Exception as exc:
            logger.warning("Gemini synthesis fallback triggered: %s", exc)

    if not final_response:
        checkpoints = []
        for item in tool_results:
            if "checkpoints" in item:
                checkpoints = item["checkpoints"]
        bullet_summary = "\n".join(f"- {cp}" for cp in checkpoints)
        final_response = (
            f"Helm Supervisor completed orchestration for: '{objective}'.\n\n"
            f"Executed MCP Plan:\n{bullet_summary}\n\n"
            "(Tip: Set GEMINI_API_KEY in backend/.env to enable live Gemini synthesis.)"
        )

    trace.append(
        TraceStep(
            node="supervisor",
            action="synthesize_and_finish",
            detail="Synthesized worker outputs and finalized orchestration run.",
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    return {
        **state,
        "next_agent": "FINISH",
        "trace": trace,
        "final_response": final_response,
    }
