from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel

from src.state.models import AgentState

load_dotenv()

RELEVANCE_SYSTEM_PROMPT = """You are a relevance classifier for a healthcare appointment booking system.

Your ONLY job is to decide whether the user's message is related to ANY of the following:
- Describing health symptoms, pain, illness, or medical conditions
- Asking to see or consult a doctor
- Booking, scheduling, or cancelling a medical appointment
- Asking about available doctors or specializations
- Any healthcare, medical, or wellness concern

If the message is about ANY of the above, classify it as relevant.
If the message is completely unrelated (e.g. weather, sports, math, general knowledge,
chitchat, programming, politics, etc.), classify it as not relevant.

Be generous — if there is ANY reasonable healthcare interpretation, mark it relevant."""


class RelevanceResult(BaseModel):
    is_relevant: bool
    reason: str


def get_relevance_llm() -> ChatGroq:
    chat_model = ChatGroq(model="openai/gpt-oss-120b")
    return chat_model.with_structured_output(RelevanceResult)


def run_relevance_check(state: AgentState) -> dict:
    llm = get_relevance_llm()
    messages: list[BaseMessage] = [
        SystemMessage(content=RELEVANCE_SYSTEM_PROMPT),
        HumanMessage(content=f"""Classify this message as relevant or not relevant to a healthcare appointment system:

<user_message>
{state.raw_message}
</user_message>

Return your classification in the requested structured format."""),
    ]

    result = llm.invoke(messages)

    if not result.is_relevant:
        return {
            "blocked": True,
            "block_reason": "I can only help with healthcare consultations and appointment booking. "
                            "Please describe your symptoms or ask about booking a doctor appointment.",
        }
    return {}
