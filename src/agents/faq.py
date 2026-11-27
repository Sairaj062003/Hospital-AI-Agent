"""FAQ / hospital-information agent.

Unlike every other agent in this project, this one does NOT hardcode which
MCP tool to call. The LLM is bound to both tools and decides - per message -
whether it needs hospital info, the doctor/specialization list, both, or
neither. This is the one place in the project where tool selection is
genuinely delegated to the model instead of being decided in Python.
"""

import json

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq

from src.mcp_server.client import get_hospital_info as _mcp_get_hospital_info
from src.mcp_server.client import list_available_doctors_and_slots as _mcp_list_slots
from src.state.models import AgentState

load_dotenv()

MAX_TOOL_ROUNDS = 3


@tool
async def get_hospital_info() -> dict:
    """Get general hospital information: visiting hours, location, emergency
    contact number, insurance policy, and parking. Use this for questions
    about the hospital itself, not about specific doctors."""
    return await _mcp_get_hospital_info()


@tool
async def list_doctors_and_specializations() -> list[dict]:
    """List doctors who currently have an open appointment slot, including
    each doctor's name and specialization. Use this to answer questions like
    'what specialists do you have' or 'do you have an ENT doctor'."""
    return await _mcp_list_slots()


FAQ_TOOLS = [get_hospital_info, list_doctors_and_specializations]
_TOOLS_BY_NAME = {t.name: t for t in FAQ_TOOLS}

FAQ_SYSTEM_PROMPT = """You are the Hospital Information Assistant for a healthcare appointment system.

You answer general, non-clinical questions about the hospital - visiting hours,
location, insurance policy, parking, emergency contact, and which doctors or
specializations are available.

Rules:
- Only answer using information returned by your tools. Never invent hours,
  policies, phone numbers, or doctor names.
- Call whichever tool(s) you need - you may need one, both, or neither.
- If a tool doesn't have the information needed to answer, say so plainly and
  suggest the patient contact the hospital directly.
- Do NOT diagnose, triage, or give medical advice. If the question turns out
  to actually be about symptoms or booking, say you can't help with that here
  and ask them to describe their symptoms directly so the system can route
  them properly.
- Be concise and friendly. Answer in plain prose, not JSON."""


def get_faq_llm() -> ChatGroq:
    chat_model = ChatGroq(model="openai/gpt-oss-120b")
    return chat_model.bind_tools(FAQ_TOOLS)


async def run_faq(state: AgentState) -> dict:
    llm = get_faq_llm()
    messages: list = [
        SystemMessage(content=FAQ_SYSTEM_PROMPT),
        HumanMessage(content=state.raw_message),
    ]

    for _ in range(MAX_TOOL_ROUNDS):
        ai_message: AIMessage = await llm.ainvoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            return {"faq_answer": ai_message.content}

        for tool_call in ai_message.tool_calls:
            tool_fn = _TOOLS_BY_NAME.get(tool_call["name"])
            if tool_fn is None:
                result = {"error": f"Unknown tool: {tool_call['name']}"}
            else:
                result = await tool_fn.ainvoke(tool_call["args"])

            messages.append(
                ToolMessage(
                    content=json.dumps(result, default=str),
                    tool_call_id=tool_call["id"],
                )
            )

    return {
        "faq_answer": "I'm having trouble answering that right now. "
                      "Please contact the hospital directly at 0223567568."
    }
