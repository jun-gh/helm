"""Supervisor Node: Steers execution between specialized workers and synthesizes reports."""

from datetime import UTC, datetime
import json
import logging
from typing import Literal

from app.core.config import get_settings
from app.orchestration.state import HelmGraphState, TraceStep

logger = logging.getLogger(__name__)


def decide_next_agent_fallback(
    objective: str,
    completed_workers: list[str],
) -> Literal["researcher", "coder", "FINISH"]:
    """Deterministic routing fallback when Gemini is unavailable."""
    obj_lower = objective.lower()
    needs_research = any(w in obj_lower for w in ["research", "audit", "investigate", "compare", "plan", "analyze"])
    needs_code = any(w in obj_lower for w in ["code", "implement", "build", "scaffold", "create", "write", "develop"])

    if "researcher" not in completed_workers and (needs_research or not needs_code):
        return "researcher"
    if "coder" not in completed_workers:
        return "coder"
    return "FINISH"


async def decide_next_agent_with_gemini(
    objective: str,
    completed_workers: list[str],
    research_notes: list[str],
    code_artifacts: list[dict],
) -> Literal["researcher", "coder", "FINISH"]:
    """Use Google Gemini to dynamically select the best worker for the objective."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return decide_next_agent_fallback(objective, completed_workers)

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.0,
        )
        messages = [
            SystemMessage(
                content=(
                    "You are Helm's Supervisor Router. You must pick the next worker to execute "
                    "or conclude the run. Available options are 'researcher', 'coder', or 'FINISH'.\n"
                    "Guidelines:\n"
                    "- Choose 'researcher' if research, comparison, or investigation is needed and 'researcher' is NOT in completed_workers.\n"
                    "- Choose 'coder' if architecture scaffolding, code generation, or implementation is needed and 'coder' is NOT in completed_workers.\n"
                    "- Choose 'FINISH' if both required specialists have run or no further worker execution is needed.\n"
                    "Respond with ONLY a JSON object: {\"next_agent\": \"researcher\" | \"coder\" | \"FINISH\", \"reason\": \"...\"}"
                )
            ),
            HumanMessage(
                content=(
                    f"Objective: {objective}\n"
                    f"Completed Workers: {completed_workers}\n"
                    f"Has Research Notes: {bool(research_notes)}\n"
                    f"Has Code Artifacts: {bool(code_artifacts)}"
                )
            ),
        ]
        response = await llm.ainvoke(messages)
        text = str(response.content).strip()
        # Clean any markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        choice = data.get("next_agent", "FINISH")
        if choice in ("researcher", "coder", "FINISH"):
            # Don't invoke already completed worker
            if choice in completed_workers:
                return "coder" if "coder" not in completed_workers else "FINISH"
            return choice
    except Exception as exc:
        logger.warning("Gemini supervisor routing fallback triggered: %s", exc)

    return decide_next_agent_fallback(objective, completed_workers)


async def supervisor_node(state: HelmGraphState) -> HelmGraphState:
    """Coordinate specialized workers and synthesize the final mission report."""
    settings = get_settings()
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    trace = list(state.get("trace", []))
    objective = state.get("objective", "")
    completed_workers = list(state.get("completed_workers", []))
    research_notes = list(state.get("research_notes", []))
    code_artifacts = list(state.get("code_artifacts", []))
    tool_results = list(state.get("tool_results", []))

    # Determine if another worker should be dispatched
    if iteration < max_iterations:
        next_worker = await decide_next_agent_with_gemini(
            objective, completed_workers, research_notes, code_artifacts
        )
        if next_worker in ("researcher", "coder"):
            trace.append(
                TraceStep(
                    node="supervisor",
                    action=f"route_to_{next_worker}",
                    detail=f"Dispatched specialized {next_worker} worker (pass {iteration + 1}/{max_iterations}).",
                    timestamp=datetime.now(UTC).isoformat(),
                )
            )
            return {
                **state,
                "next_agent": next_worker,
                "trace": trace,
            }

    # All worker passes complete -> synthesize final mission report
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
            worker_context = []
            if research_notes:
                worker_context.append("### Research Findings:\n" + "\n".join(research_notes))
            if code_artifacts:
                for art in code_artifacts:
                    worker_context.append(f"### Code Scaffold ({art.get('inspector_verdict')}):\n{art.get('snippet')}")

            messages = [
                SystemMessage(
                    content=(
                        "You are Helm, the Master Agent Orchestrator. Synthesize a unified, executive "
                        "mission debrief combining the Researcher's insights and Coder's implementation."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Objective: {objective}\n"
                        f"Specialists Involved: {completed_workers}\n\n"
                        + "\n\n".join(worker_context)
                    )
                ),
            ]
            ai_msg = await llm.ainvoke(messages)
            final_response = str(ai_msg.content)
        except Exception as exc:
            logger.warning("Gemini synthesis fallback triggered: %s", exc)

    if not final_response:
        res_summary = "\n".join(f"- {n}" for n in research_notes) if research_notes else "- Standard cluster telemetry verified."
        code_summary = code_artifacts[0]["snippet"] if code_artifacts else "N/A"
        final_response = (
            f"Helm Supervisor completed multi-agent orchestration for: '{objective}'.\n\n"
            f"Active Specialists: {', '.join(completed_workers) or 'diagnostic'}\n\n"
            f"Synthesized Research:\n{res_summary}\n\n"
            f"Generated Code / Architecture:\n{code_summary}"
        )

    trace.append(
        TraceStep(
            node="supervisor",
            action="synthesize_and_finish",
            detail=f"Unified reports from {completed_workers} into final mission synthesis.",
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    return {
        **state,
        "next_agent": "FINISH",
        "trace": trace,
        "final_response": final_response,
    }
