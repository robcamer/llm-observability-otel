from typing import TypedDict, Any
from langgraph.graph import StateGraph
from .agents import planner_agent, worker_agent, reflection_agent, reviewer_agent


class GraphState(TypedDict, total=False):
    task: str
    plan: str
    work: str
    reflection: str
    review: str


# Build a simple linear multi-agent workflow: planner -> worker -> reviewer


def build_graph() -> Any:
    graph = StateGraph(GraphState)

    graph.add_node("planner", planner_agent)
    graph.add_node("worker", worker_agent)
    # Node name must differ from state key to avoid collision; use 'reflector'
    graph.add_node("reflector", reflection_agent)
    graph.add_node("reviewer", reviewer_agent)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "worker")
    graph.add_edge("worker", "reflector")
    graph.add_edge("reflector", "reviewer")

    graph.set_finish_point("reviewer")
    return graph.compile()


__all__ = ["build_graph", "GraphState"]
