"""LangGraph StateGraph compilation for the Helm Multi-Worker Orchestrator."""

from langgraph.graph import END, START, StateGraph

from app.orchestration.nodes.coder import coder_node
from app.orchestration.nodes.researcher import researcher_node
from app.orchestration.nodes.supervisor import supervisor_node
from app.orchestration.state import HelmGraphState


def route_from_supervisor(state: HelmGraphState) -> str:
    """Conditional edge routing from Supervisor to specialized Workers or END."""
    next_agent = state.get("next_agent", "FINISH")
    if next_agent in ("researcher", "coder"):
        return next_agent
    return END


def build_helm_graph():
    """Construct and compile the Helm Multi-Worker (Supervisor, Researcher, Coder) StateGraph."""
    workflow = StateGraph(HelmGraphState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("coder", coder_node)

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "researcher": "researcher",
            "coder": "coder",
            END: END,
        },
    )
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("coder", "supervisor")

    return workflow.compile()


helm_graph = build_helm_graph()
