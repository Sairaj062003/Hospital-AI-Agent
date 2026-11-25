from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.state.models import AgentState, RedactedPatientInput, TriageResult, UrgencyLevel

load_dotenv()


TRIAGE_SYSTEM_PROMPT = """You are the Triage Agent for a healthcare assistant.
Your only job is to assess the urgency of a patient's condition based on their
already-extracted, structured symptoms and stated need.

Do not diagnose conditions or recommend treatment.
Classify urgency as one of: low, medium, high, emergency.
If there is any sign of a life-threatening or emergency situation, set urgency to
"emergency" and escalate_to_human to true."""


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


def validate_triage_output(result: TriageResult , redacted_input: RedactedPatientInput) -> TriageResult:
        emergency_keywords = [
            "chest pain",
            "can't breathe",
            "cannot breathe",
            "unconscious",
            "severe bleeding",
            "suicidal",
        ]
        patient_text = f"{redacted_input.stated_symptoms} {redacted_input.stated_need}".lower()
        if (
            result.urgency != UrgencyLevel.EMERGENCY
            and any(keyword in patient_text for keyword in emergency_keywords)
        ):
            raise ValueError(
                "Triage output contradicts clearly emergency symptoms - possible manipulation"
            )
        if result.urgency == UrgencyLevel.EMERGENCY and not result.escalate_to_human:
           raise ValueError("Emergency urgency must always have escalate_to_human=True.")
        if not result.rationale:
           raise ValueError("rationale is required in the triage output.")
     
        return result


def run_triage(state: AgentState) -> dict:
    result = run_triage_llm(state.redacted_input)
    result = validate_triage_output(result, state.redacted_input)
    return {"triage": result}
