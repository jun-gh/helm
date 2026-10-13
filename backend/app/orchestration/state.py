"""Shared graph state definition for Helm multi-agent coordination."""

from typing import Any, Literal, TypedDict


class TraceStep(TypedDict):
    """Single step in the agent execution trace."""

    node: str
    action: str
    detail: str
    timestamp: str


class HelmGraphState(TypedDict, total=False):
    """State dictionary passed between Supervisor and specialized Worker nodes in LangGraph."""

    thread_id: str
    objective: str
    next_agent: Literal["researcher", "coder", "FINISH"]
    iteration: int
    max_iterations: int
    completed_workers: list[str]
    research_notes: list[str]
    code_artifacts: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    trace: list[TraceStep]
    final_response: str
