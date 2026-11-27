from typing import Optional

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.state.models import AgentState, RedactedPatientInput, TriageResult, UrgencyLevel

load_dotenv()

EMERGENCY_KEYWORDS = (
    "chest pain",
    "can't breathe",
    "cant breathe",
    "cannot breathe",
    "unconscious",
    "severe bleeding",
    "suicidal",
)


TRIAGE_SYSTEM_PROMPT = """You are the Triage Agent for a healthcare appointment booking system.
Your ONLY job is to assess the urgency of a patient's condition and decide whether
a human staff member needs to review the case before proceeding.

Urgency levels (pick exactly one):
- low: routine checkup, mild or chronic symptoms with no acute danger
  (e.g. mild headache, skin rash, routine eye exam)
- medium: symptoms that need attention soon but are not immediately dangerous
  (e.g. persistent fever, recurring pain, moderate infection signs)
- high: symptoms that could worsen quickly without prompt care
  (e.g. high fever with breathing difficulty, severe abdominal pain, significant injury)
- emergency: potentially life-threatening — immediate intervention needed
  (e.g. chest pain, inability to breathe, unconsciousness, severe bleeding, suicidal ideation)

Rules:
- If urgency is "emergency", you MUST set escalate_to_human to true.
- For "high" urgency, set escalate_to_human to true as well — these cases benefit
  from staff review before booking.
- For "low" and "medium", set escalate_to_human to false.
- Write a clear, concise rationale (2-3 sentences) explaining WHY you chose that
  urgency level, referencing the specific symptoms that drove your decision.
- Do NOT diagnose conditions or name specific diseases. Do NOT recommend treatment.
- When in doubt between two levels, pick the higher one — err on the side of caution."""


def get_triage_llm() -> ChatGroq:
    chat_model = ChatGroq(model="openai/gpt-oss-120b")
    return chat_model.with_structured_output(TriageResult)


def build_triage_prompt(redacted_input: RedactedPatientInput) -> list[BaseMessage]:
    human_content = f"""Assess the urgency of the following patient intake data:

<stated_symptoms>
{redacted_input.stated_symptoms}
</stated_symptoms>

<stated_need>
{redacted_input.stated_need}
</stated_need>

Return the urgency assessment in the requested structured format."""

    return [
        SystemMessage(content=TRIAGE_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]


def run_triage_llm(redacted_input: RedactedPatientInput) -> TriageResult:
    llm = get_triage_llm()
    prompt = build_triage_prompt(redacted_input)
    return llm.invoke(prompt)


def find_emergency_keyword(texts: list[Optional[str]]) -> Optional[str]:
    # Phone keyboards type a curly apostrophe, e.g. "can’t breathe".
    patient_text = " ".join(text for text in texts if text).lower().replace("’", "'")
    return next((keyword for keyword in EMERGENCY_KEYWORDS if keyword in patient_text), None)


def validate_triage_output(
    result: TriageResult,
    redacted_input: RedactedPatientInput,
    patient_message: Optional[str] = None,
) -> TriageResult:
    """Enforce the safety rules in code.

    A wrong AI answer is corrected, not rejected, so the case always reaches staff.
    Urgency and escalation are only ever raised, never lowered. Keyword matching
    ignores negation ("no chest pain"), so staff make the final call on those.
    """
    urgency = result.urgency
    rationale = result.rationale.strip() or "The AI gave no explanation."

    keyword = find_emergency_keyword(
        [patient_message, *redacted_input.stated_symptoms, redacted_input.stated_need]
    )
    if keyword and urgency != UrgencyLevel.EMERGENCY:
        rationale += (
            f' Safety rule: raised from {urgency.value} to emergency because the '
            f'message mentions "{keyword}".'
        )
        urgency = UrgencyLevel.EMERGENCY

    must_escalate = urgency in (UrgencyLevel.HIGH, UrgencyLevel.EMERGENCY)
    return TriageResult(
        urgency=urgency,
        escalate_to_human=result.escalate_to_human or must_escalate,
        rationale=rationale,
    )


def run_triage(state: AgentState) -> dict:
    result = run_triage_llm(state.redacted_input)
    result = validate_triage_output(result, state.redacted_input, state.redacted_raw_message)
    return {"triage": result}
