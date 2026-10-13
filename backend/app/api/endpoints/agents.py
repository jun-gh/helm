"""Agent orchestration endpoints for steering LangGraph workflows."""

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OrchestrationRunLog
from app.db.session import get_db_session
from app.memory.firestore_store import state_store
from app.orchestration.graph import helm_graph
from app.orchestration.state import HelmGraphState, TraceStep

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    """Request payload for triggering a Helm orchestration run."""

    objective: str = Field(..., min_length=3, max_length=2000)
    thread_id: str | None = Field(default=None)
    max_iterations: int = Field(default=3, ge=1, le=5)


class AgentRunResponse(BaseModel):
    """Response payload containing the orchestration output and node trace."""

    thread_id: str
    objective: str
    final_response: str
    trace: list[TraceStep]
    completed_workers: list[str] = Field(default_factory=list)
    research_notes: list[str] = Field(default_factory=list)
    code_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]]
    state_backend: str


@router.post("/run", response_model=AgentRunResponse)
async def run_orchestration(
    payload: AgentRunRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AgentRunResponse:
    """Execute the Helm LangGraph Multi-Worker workflow and persist state."""
    thread_id = payload.thread_id or f"helm-{uuid4().hex[:10]}"

    initial_state: HelmGraphState = {
        "thread_id": thread_id,
        "objective": payload.objective,
        "iteration": 0,
        "max_iterations": payload.max_iterations,
        "completed_workers": [],
        "research_notes": [],
        "code_artifacts": [],
        "tool_results": [],
        "trace": [],
        "final_response": "",
    }

    final_state: HelmGraphState = await helm_graph.ainvoke(initial_state)

    # Persist state checkpoint to Firestore (or local memory fallback)
    await state_store.save_checkpoint(thread_id, dict(final_state))

    # Persist audit log to SQLite (local) or Neon Serverless Postgres (prod)
    run_log = OrchestrationRunLog(
        thread_id=thread_id,
        objective=payload.objective,
        status="completed",
        final_output=final_state.get("final_response", ""),
    )
    db.add(run_log)
    await db.commit()

    return AgentRunResponse(
        thread_id=thread_id,
        objective=payload.objective,
        final_response=final_state.get("final_response", ""),
        trace=final_state.get("trace", []),
        completed_workers=final_state.get("completed_workers", []),
        research_notes=final_state.get("research_notes", []),
        code_artifacts=final_state.get("code_artifacts", []),
        tool_results=final_state.get("tool_results", []),
        state_backend=state_store.backend_mode,
    )


@router.get("/checkpoints/{thread_id}")
async def get_thread_checkpoint(thread_id: str) -> dict[str, Any]:
    """Retrieve a saved thread checkpoint from Firestore / memory store."""
    checkpoint = await state_store.load_checkpoint(thread_id)
    if checkpoint is None:
        return {"thread_id": thread_id, "found": False, "state": None}
    return {"thread_id": thread_id, "found": True, **checkpoint}
