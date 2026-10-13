"""Worker Node: Executes MCP tools on behalf of the Supervisor."""

from datetime import UTC, datetime

from app.mcp_layer.client import mcp_registry
from app.orchestration.state import HelmGraphState, TraceStep


async def worker_node(state: HelmGraphState) -> HelmGraphState:
    """Invoke MCP tools to gather telemetry and task plans for the objective."""
    objective = state.get("objective", "")
    iteration = state.get("iteration", 0) + 1
    trace = list(state.get("trace", []))
    tool_results = list(state.get("tool_results", []))

    plan_output = await mcp_registry.invoke_tool(
        "helm_task_planner", {"objective": objective}
    )
    telemetry_output = await mcp_registry.invoke_tool(
        "helm_cluster_telemetry", {"component": "all"}
    )

    tool_results.extend([plan_output, telemetry_output])
    trace.append(
        TraceStep(
            node="worker",
            action="invoke_mcp_tools",
            detail="Executed MCP tools: helm_task_planner, helm_cluster_telemetry.",
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    return {
        **state,
        "iteration": iteration,
        "tool_results": tool_results,
        "trace": trace,
    }
