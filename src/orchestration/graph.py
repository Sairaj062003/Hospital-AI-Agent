from langgraph.graph import StateGraph, END

from src.agents.intake import run_intake
from src.agents.scheduling import run_scheduling
from src.agents.triage import run_triage
from src.state.models import AgentState


def human_review_node(state: AgentState) -> dict:
    print(f"[HUMAN REVIEW REQUIRED] urgency={state.triage.urgency}, rationale={state.triage.rationale}")
    return {}


def route_after_triage(state: AgentState) -> str:
    if state.triage.escalate_to_human:
        return "human_review"
    return "scheduling"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("intake", run_intake)
    graph.add_node("triage", run_triage)
    graph.add_node("scheduling", run_scheduling)
    graph.add_node("human_review", human_review_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "triage")
    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {"scheduling": "scheduling", "human_review": "human_review"},
    )
    graph.add_edge("scheduling", END)
    graph.add_edge("human_review", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()
    result = app.invoke(AgentState(raw_message="I've had chest pain since this morning and I'm scared. Can someone see me today?"))
    print(result)
