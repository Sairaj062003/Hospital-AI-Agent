from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.types import interrupt

from src.mcp_server.client import book_slot, list_available_doctors_and_slots
from src.state.models import (
    AgentState,
    RedactedPatientInput,
    SchedulingOutcome,
    SchedulingRecommendation,
)

load_dotenv()


SCHEDULING_SYSTEM_PROMPT = """You are the Scheduling Agent for a healthcare assistant.
Your only job is to recommend the single most appropriate appointment slot based on
the patient's stated need and the list of currently available doctors and slots. Pay
attention to each doctor's specialization - recommend a doctor whose specialization
actually matches what the patient needs, not just the earliest available slot.

You never book an appointment yourself - you only recommend a slot_id. The decision
to actually book is made by code outside of you, after a human confirms the choice.

Return the recommended slot in the requested structured format."""


def get_scheduling_llm() -> ChatGroq:
    chat_model = ChatGroq(model="openai/gpt-oss-120b")
    return chat_model.with_structured_output(SchedulingRecommendation)


def build_scheduling_prompt(
    redacted_input: RedactedPatientInput, available_slots: list[dict]
) -> list[BaseMessage]:
    human_content = f"""Recommend an appointment slot for this patient:

<stated_need>
{redacted_input.stated_need}
</stated_need>

<stated_symptoms>
{redacted_input.stated_symptoms}
</stated_symptoms>

<available_doctors_and_slots>
{available_slots}
</available_doctors_and_slots>

Return the recommended slot in the requested structured format."""

    return [
        SystemMessage(content=SCHEDULING_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]


def run_scheduling_llm(
    redacted_input: RedactedPatientInput, available_slots: list[dict]
) -> SchedulingRecommendation:
    llm = get_scheduling_llm()
    prompt = build_scheduling_prompt(redacted_input, available_slots)
    return llm.invoke(prompt)


def validate_scheduling_output(
    result: SchedulingRecommendation, available_slots: list[dict]
) -> SchedulingRecommendation:
    if not result.recommended_slot_id:
        raise ValueError("recommended_slot_id is required in the scheduling output.")
    if not result.reasoning:
        raise ValueError("reasoning is required in the scheduling output.")
    valid_ids = {slot["slot_id"] for slot in available_slots}
    if result.recommended_slot_id not in valid_ids:
        raise ValueError(
            f"recommended_slot_id {result.recommended_slot_id!r} is not an available slot."
        )
    return result


async def run_scheduling(state: AgentState) -> dict:
    available_slots = await list_available_doctors_and_slots()
    recommendation = run_scheduling_llm(state.redacted_input, available_slots)
    recommendation = validate_scheduling_output(recommendation, available_slots)

    chosen_slot_id = interrupt({
        "reason": "choose_slot",
        "available_slots": available_slots,
        "recommended_slot_id": recommendation.recommended_slot_id,
        "reasoning": recommendation.reasoning,
    })

    valid_ids = {slot["slot_id"] for slot in available_slots}
    if chosen_slot_id not in valid_ids:
        raise ValueError(f"chosen_slot_id {chosen_slot_id!r} is not an available slot.")

    booked = await book_slot(chosen_slot_id)
    if not booked:
        raise ValueError(
            f"Could not book slot {chosen_slot_id!r} - it may have just been booked "
            "by someone else."
        )

    outcome = SchedulingOutcome(
        recommendation=recommendation,
        requires_approval=True,
        booked=True,
        booked_slot_id=chosen_slot_id,
    )
    return {"scheduling_result": outcome}
