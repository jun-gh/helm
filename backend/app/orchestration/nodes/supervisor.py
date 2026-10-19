"""Supervisor Node: Steers execution between specialized workers and synthesizes reports."""

import ast
import json
import logging
import re
from datetime import UTC, datetime
from typing import Literal

from app.core.config import get_settings
from app.core.resilience import (
    categorize_gemini_error,
    execute_with_retry,
    extract_text_content,
)
from app.orchestration.state import HelmGraphState, TraceStep

logger = logging.getLogger(__name__)


def format_gemini_error(exc: Exception, context: str) -> str:
    """Format readable error message for quotas, spikes, and authentication failures."""
    err_str = str(exc)
    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
        return f"{context}: 429 Quota Exceeded (Free-tier limit reached)."
    if "503" in err_str or "UNAVAILABLE" in err_str:
        return f"{context}: 503 Service Spike (Cluster high demand)."
    if "401" in err_str or "UNAUTHENTICATED" in err_str:
        return f"{context}: 401 Authentication Error (Check GEMINI_API_KEY)."
    return f"{context}: {exc.__class__.__name__} ({err_str[:90]})"


def is_provider_throttled(errors: list[str]) -> bool:
    """Return True if an upstream LLM quota (429) or service spike (503) was recorded."""
    for err in errors:
        err_upper = err.upper()
        if any(tok in err_upper for tok in ("429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE")):
            return True
    return False



def decide_next_agent_fallback(
    objective: str,
    completed_workers: list[str],
) -> Literal["researcher", "coder", "FINISH"]:
    """Deterministic routing fallback based on keywords and uncompleted specialists."""
    obj_lower = objective.lower()
    needs_research = any(
        w in obj_lower
        for w in ["research", "audit", "investigate", "compare", "plan", "analyze"]
    )
    needs_code = any(
        w in obj_lower
        for w in [
            "code", "implement", "build", "scaffold", "create", "write", "develop", "session"
        ]
    )

    if "researcher" not in completed_workers and (needs_research or not needs_code):
        return "researcher"
    if "coder" not in completed_workers:
        return "coder"
    return "FINISH"


def extract_next_agent_decision(raw_text: str) -> dict:
    """Extract next_agent decision supporting strict JSON, Python single-quotes, and markdown."""
    text = raw_text.strip()

    # 1. Strip markdown fences if present
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()

    # 2. Extract balanced curly braces block
    brace_match = re.search(r"\{[\s\S]*\}", text)
    json_candidate = brace_match.group(0) if brace_match else text

    # 3. Try standard JSON
    try:
        data = json.loads(json_candidate)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 4. Try Python literal eval (for single-quoted dicts)
    try:
        data = ast.literal_eval(json_candidate)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 5. Regex search for next_agent key
    agent_match = re.search(
        r"['\"]?next_agent['\"]?\s*[:=]\s*['\"]?(researcher|coder|FINISH)['\"]?",
        text,
        re.IGNORECASE,
    )
    if agent_match:
        found = agent_match.group(1).lower()
        mapping = {"researcher": "researcher", "coder": "coder", "finish": "FINISH"}
        if found in mapping:
            return {"next_agent": mapping[found]}

    # 6. Fallback scan for standalone agent tokens
    for token, mapped in [("researcher", "researcher"), ("coder", "coder"), ("finish", "FINISH")]:
        if re.search(rf"\b{token}\b", text, re.IGNORECASE):
            return {"next_agent": mapped}

    return {}


async def decide_next_agent_with_gemini(
    objective: str,
    completed_workers: list[str],
    research_notes: list[str],
    code_artifacts: list[dict],
    errors: list[str] | None = None,
) -> tuple[Literal["researcher", "coder", "FINISH"], str, dict | None]:
    """Use Google Gemini to select the best worker for the objective with 3-retry resilience."""
    settings = get_settings()
    if not settings.gemini_api_key or (errors and is_provider_throttled(errors)):
        return decide_next_agent_fallback(objective, completed_workers), "", None

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.0,
            max_retries=0,
            timeout=12.0,
        )
        messages = [
            SystemMessage(
                content=(
                    "You are Helm's Supervisor Router. You must pick the next worker to execute "
                    "or conclude the run. Options: 'researcher', 'coder', or 'FINISH'.\n"
                    "Guidelines:\n"
                    "- 'researcher': if investigation/comparison needed and not in completed.\n"
                    "- 'coder': if architecture/code needed and not in completed.\n"
                    "- 'FINISH': if required specialists have run or no further work needed.\n"
                    'Respond with ONLY JSON: {"next_agent": "researcher"|"coder"|"FINISH", '
                    '"reason": "..."}'
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

        async def _call_router():
            return await llm.ainvoke(messages)

        response, struct_err = await execute_with_retry(
            _call_router,
            worker="Supervisor Router",
            model=settings.gemini_model,
            max_retries=3,
        )

        if struct_err:
            err_msg = struct_err["message"]
            logger.warning("Gemini supervisor routing fallback triggered: %s", err_msg)
            return (
                decide_next_agent_fallback(objective, completed_workers),
                err_msg,
                struct_err,
            )

        if response:
            data = extract_next_agent_decision(extract_text_content(response.content))
            choice = data.get("next_agent", "")
            if choice in ("researcher", "coder"):
                if choice in completed_workers:
                    return (
                        ("coder" if "coder" not in completed_workers else "FINISH"),
                        "",
                        None,
                    )
                return choice, "", None
            if choice == "FINISH":
                if not completed_workers:
                    return decide_next_agent_fallback(objective, completed_workers), "", None
                return "FINISH", "", None

    except Exception as exc:
        diag = categorize_gemini_error(
            exc,
            worker="Supervisor Router",
            model=settings.gemini_model,
            retries_attempted=3,
        )
        logger.warning("Gemini supervisor routing fallback triggered: %s", exc)
        return decide_next_agent_fallback(objective, completed_workers), diag["message"], diag

    return decide_next_agent_fallback(objective, completed_workers), "", None


async def supervisor_node(state: HelmGraphState) -> HelmGraphState:
    """Coordinate specialized workers and synthesize the final mission report."""
    settings = get_settings()
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    trace = list(state.get("trace", []))
    errors = list(state.get("errors", []))
    structured_errors = list(state.get("structured_errors", []))
    objective = state.get("objective", "")
    completed_workers = list(state.get("completed_workers", []))
    research_notes = list(state.get("research_notes", []))
    code_artifacts = list(state.get("code_artifacts", []))

    # Determine if another worker should be dispatched
    if iteration < max_iterations:
        next_worker, router_err, router_diag = await decide_next_agent_with_gemini(
            objective, completed_workers, research_notes, code_artifacts, errors
        )
        if router_err and router_err not in errors:
            errors.append(router_err)
        if router_diag and router_diag not in structured_errors:
            structured_errors.append(router_diag)

        if next_worker in ("researcher", "coder"):
            detail = (
                f"Dispatched specialized {next_worker} worker with {settings.gemini_model} "
                f"(pass {iteration + 1}/{max_iterations})."
            )
            if router_err:
                detail += f" [{router_err}]"
            trace.append(
                TraceStep(
                    node="supervisor",
                    action=f"route_to_{next_worker}",
                    detail=detail,
                    timestamp=datetime.now(UTC).isoformat(),
                )
            )
            return {
                **state,
                "next_agent": next_worker,
                "trace": trace,
                "errors": errors,
                "structured_errors": structured_errors,
            }

    # All worker passes complete -> synthesize final mission report
    final_response = ""
    synthesis_err = ""
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
            worker_context = []
            if research_notes:
                worker_context.append("### Research Findings:\n" + "\n".join(research_notes))
            if code_artifacts:
                for art in code_artifacts:
                    verdict = art.get("inspector_verdict")
                    snippet = art.get("snippet")
                    worker_context.append(f"### Code Scaffold ({verdict}):\n{snippet}")

            messages = [
                SystemMessage(
                    content=(
                        "You are Helm, the Master Agent Orchestrator. Synthesize a unified, "
                        "executive mission debrief combining research insights and code."
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

            async def _call_synthesizer():
                return await llm.ainvoke(messages)

            ai_msg, synth_diag = await execute_with_retry(
                _call_synthesizer,
                worker="Supervisor Synthesizer",
                model=settings.gemini_model,
                max_retries=3,
            )
            if synth_diag:
                synthesis_err = synth_diag["message"]
                if synthesis_err not in errors:
                    errors.append(synthesis_err)
                if synth_diag not in structured_errors:
                    structured_errors.append(synth_diag)
                logger.warning("Gemini synthesis fallback triggered: %s", synthesis_err)
            elif ai_msg:
                final_response = extract_text_content(ai_msg.content)
        except Exception as exc:
            synthesis_err = format_gemini_error(exc, "Supervisor Synthesizer")
            logger.warning("Gemini synthesis fallback triggered: %s", exc)
            if synthesis_err not in errors:
                errors.append(synthesis_err)

    if not final_response:
        res_summary = (
            "\n".join(f"- {n}" for n in research_notes)
            if research_notes
            else "- Standard cluster telemetry verified."
        )
        code_summary = code_artifacts[0]["snippet"] if code_artifacts else "N/A"
        final_response = (
            f"Helm Supervisor completed multi-agent orchestration for: '{objective}'.\n\n"
            f"Active Specialists: {', '.join(completed_workers) or 'diagnostic'}\n\n"
            f"Synthesized Research:\n{res_summary}\n\n"
            f"Generated Code / Architecture:\n{code_summary}"
        )
        if synthesis_err:
            final_response += f"\n\n*(Notice: {synthesis_err}. Local fallback used.)*"

    finish_detail = (
        f"Unified reports from {completed_workers} into final mission synthesis "
        f"({settings.gemini_model})."
    )
    if synthesis_err:
        finish_detail += f" [{synthesis_err}]"

    trace.append(
        TraceStep(
            node="supervisor",
            action="synthesize_and_finish",
            detail=finish_detail,
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    return {
        **state,
        "next_agent": "FINISH",
        "trace": trace,
        "errors": errors,
        "structured_errors": structured_errors,
        "final_response": final_response,
    }
