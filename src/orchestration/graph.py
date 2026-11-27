import asyncio
import sys

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.types import Command, interrupt

from src.agents.faq import run_faq
from src.agents.intake import run_intake
from src.agents.scheduling import run_scheduling
from src.agents.triage import run_triage
from src.security.pii import run_pii_redaction
from src.state.models import AgentState
from src.guardrails.injection import run_injection_guard
from src.guardrails.relevance import run_relevance_check

def human_review_node(state: AgentState) -> dict:
    contact = state.contact
    review = interrupt({
        "reason": "escalate_to_human",
        "raw_message": state.raw_message,
        "full_name": contact.full_name if contact else None,
        "phone_number": contact.phone_number if contact else None,
        "urgency": state.triage.urgency.value,
        "rationale": state.triage.rationale,
        "prompt": "Tell patient to contact authorities immediately? (yes/no)",
    })

    if review["decision"] == "yes":
        return {"emergency_message": review["message"]}
    return {"admin_message": review["message"]}


def blocked_node(state: AgentState) -> dict:
    print(f"[BLOCKED] {state.block_reason}")
    return {}


def route_after_triage(state: AgentState) -> str:
    if state.triage.escalate_to_human:
        return "human_review"
    return "scheduling_step"

def route_after_injection_guard(state: AgentState) -> str:
    if state.blocked:
        return "blocked"
    return "relevance_check"

def route_after_relevance(state: AgentState) -> str:
    if state.blocked:
        return "blocked"
    if state.message_category == "informational":
        return "faq_step"
    return "pii_redaction"

def route_after_human_review(state: AgentState) -> str:
    if state.emergency_message:
        return "end"
    return "scheduling_step"

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("pii_redaction", run_pii_redaction)
    graph.add_node("injection_guard", run_injection_guard)
    graph.add_node("relevance_check", run_relevance_check)

    graph.add_node("intake_step", run_intake)
    graph.add_node("triage_step", run_triage)
    graph.add_node("scheduling_step", run_scheduling)
    graph.add_node("human_review", human_review_node)
    graph.add_node("blocked_step", blocked_node)
    graph.add_node("faq_step", run_faq)

    graph.set_entry_point("injection_guard")
    graph.add_conditional_edges(
        "injection_guard", route_after_injection_guard,
        {"blocked": "blocked_step", "relevance_check": "relevance_check"}
    )
    graph.add_conditional_edges(
        "relevance_check", route_after_relevance,
        {"blocked": "blocked_step", "faq_step": "faq_step", "pii_redaction": "pii_redaction"}
    )
    graph.add_edge("blocked_step", END)
    graph.add_edge("faq_step", END)
    graph.add_edge("pii_redaction", "intake_step")
    graph.add_edge("intake_step", "triage_step")
    graph.add_conditional_edges(
        "triage_step",
        route_after_triage,
        {"scheduling_step": "scheduling_step", "human_review": "human_review"},

    )
    
    graph.add_conditional_edges(
    "human_review", route_after_human_review,
    {"end": END, "scheduling_step": "scheduling_step"},
     )
    graph.add_edge("scheduling_step", END)

    return graph.compile(checkpointer=MemorySaver())


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    app = build_graph()
    config = {"configurable": {"thread_id": "demo-1"}}

    result = await app.ainvoke(
        AgentState(raw_message="I have had severe chest pain since this morning, please help"),
        config=config,
    )

    snapshot = await app.aget_state(config)
    while snapshot.next:
        payload = snapshot.tasks[0].interrupts[0].value
        print("Paused:", payload)

        if payload.get("reason") == "choose_slot":
            answer = int(input("Enter slot_id to book: "))
        else:
            decision = input(payload.get("prompt", "Decision: ") + " ")
            answer = {"decision": decision, "message": input("Message to patient: ")}

        result = await app.ainvoke(Command(resume=answer), config=config)
        snapshot = await app.aget_state(config)

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
