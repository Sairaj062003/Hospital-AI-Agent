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


SCHEDULING_SYSTEM_PROMPT = """You are the Scheduling Agent for a healthcare appointment booking system.

Your job:
1. From the patient's symptoms and stated need, determine which medical specialization
   they need. You MUST pick a value that EXACTLY matches one of the "specialization"
   values in the available doctors list below — do not paraphrase, abbreviate, or
   invent a specialization.

   Common mappings (use these as guidance, not as a rigid lookup):
   - Chest pain, heart palpitations, blood pressure → Cardiology
   - Skin rash, acne, eczema → Dermatology
   - Bone/joint pain, fracture, back pain → Orthopedics
   - Headache, dizziness, numbness, seizures → Neurology
   - Eye problems, blurred vision → Ophthalmology
   - Ear/nose/throat, hearing loss, sinusitis → ENT
   - Kidney pain, urinary issues → Nephrology
   - Breathing difficulty, cough, asthma → Pulmonology
   - Stomach pain, digestion issues, nausea → Gastroenterology
   - Child health, pediatric concerns → Pediatrics
   - Mental health, anxiety, depression → Psychiatry
   - Women's health, pregnancy → Gynecology
   - General/vague symptoms, fever, fatigue → General Medicine

   If the symptoms don't clearly map to a specialty, choose "General Medicine".

2. Recommend the single best slot_id from doctors who have that specialization —
   prefer the earliest available slot unless the patient's need suggests otherwise.

You never book an appointment — you only recommend. The patient confirms the choice.

Return the specialization and recommended slot in the requested structured format."""


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
    if not result.required_specialization:
        raise ValueError("required_specialization is required in the scheduling output.")

    slots_by_id = {slot["slot_id"]: slot for slot in available_slots}
    if result.recommended_slot_id not in slots_by_id:
        raise ValueError(
            f"recommended_slot_id {result.recommended_slot_id!r} is not an available slot."
        )

    valid_specializations = {slot["specialization"] for slot in available_slots}
    if result.required_specialization not in valid_specializations:
        raise ValueError(
            f"required_specialization {result.required_specialization!r} does not match "
            "any specialization actually present in the available slots."
        )

    recommended_slot = slots_by_id[result.recommended_slot_id]
    if recommended_slot["specialization"] != result.required_specialization:
        raise ValueError(
            f"recommended_slot_id {result.recommended_slot_id!r} belongs to "
            f"{recommended_slot['specialization']!r}, which does not match the "
            f"determined required_specialization {result.required_specialization!r}."
        )

    return result


async def run_scheduling(state: AgentState) -> dict:
    available_slots = await list_available_doctors_and_slots()
    recommendation = run_scheduling_llm(state.redacted_input, available_slots)
    recommendation = validate_scheduling_output(recommendation, available_slots)

    # Only slots matching the determined specialization are shown to the
    # patient - this is a code-enforced filter, not just LLM free-text
    # reasoning, so the patient never sees irrelevant specialists.
    matching_slots = [
        slot for slot in available_slots
        if slot["specialization"] == recommendation.required_specialization
    ]

    if not matching_slots:
        interrupt({
            "reason": "no_slots",
            "required_specialization": recommendation.required_specialization,
        })
        return {
            "scheduling_result": SchedulingOutcome(
                recommendation=recommendation,
                requires_approval=False,
                booked=False,
            )
        }

    chosen_slot_id = interrupt({
        "reason": "choose_slot",
        "required_specialization": recommendation.required_specialization,
        "available_slots": matching_slots,
        "recommended_slot_id": recommendation.recommended_slot_id,
        "reasoning": recommendation.reasoning,
    })

    valid_ids = {slot["slot_id"] for slot in matching_slots}
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
