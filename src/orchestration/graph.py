import sys

from langgraph.graph import StateGraph, END

from src.agents.intake import run_intake
from src.agents.scheduling import run_scheduling
from src.agents.triage import run_triage
from src.security.pii import run_pii_redaction
from src.state.models import AgentState
from src.security.pii import run_pii_redaction

def human_review_node(state: AgentState) -> dict:
    print(f"[HUMAN REVIEW REQUIRED] urgency={state.triage.urgency}, rationale={state.triage.rationale}")
    return {}


def route_after_triage(state: AgentState) -> str:
    if state.triage.escalate_to_human:
        return "human_review"
    return "scheduling_step"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("pii_redaction", run_pii_redaction)
    
    graph.add_node("intake_step", run_intake)
    graph.add_node("triage_step", run_triage)
    graph.add_node("scheduling_step", run_scheduling)
    graph.add_node("human_review", human_review_node)

    graph.set_entry_point("pii_redaction")
    graph.add_edge("pii_redaction", "intake_step")
    graph.add_edge("intake_step", "triage_step")
    graph.add_conditional_edges(
        "triage_step",
        route_after_triage,
        {"scheduling_step": "scheduling_step", "human_review": "human_review"},
    )
    graph.add_edge("scheduling_step", END)
    graph.add_edge("human_review", END)

    return graph.compile()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    app = build_graph()
    result = app.invoke(AgentState(raw_message="Im fiver since this morning. Can someone see me today?"))
    print(result)
