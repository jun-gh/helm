"""LangGraph StateGraph compilation for the Helm Orchestrator."""

from langgraph.graph import END, START, StateGraph

from app.orchestration.nodes.supervisor import supervisor_node
from app.orchestration.nodes.worker import worker_node
from app.orchestration.state import HelmGraphState


def route_from_supervisor(state: HelmGraphState) -> str:
    """Conditional edge routing from Supervisor to Worker or END."""
    if state.get("next_agent") == "worker":
        return "worker"
    return END


def build_helm_graph():
    """Construct and compile the Helm Supervisor-Worker StateGraph."""
    workflow = StateGraph(HelmGraphState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("worker", worker_node)

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "worker": "worker",
            END: END,
        },
    )
    workflow.add_edge("worker", "supervisor")

    return workflow.compile()


helm_graph = build_helm_graph()
