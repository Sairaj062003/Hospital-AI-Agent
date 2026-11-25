"""FastAPI layer exposing the LangGraph pipeline and appointment data over HTTP.

Two different kinds of pauses happen inside the graph, and this API treats
them very differently:

- human_review ("tell the patient to contact authorities?") is answered by
  whoever is running this server, right here in its own console via a
  blocking input() call. It never reaches the frontend.
- scheduling_step's choose_slot pause IS patient-facing: the frontend shows
  the available doctors/slots and the patient picks one, which becomes a
  separate /api/resume call.
"""

import asyncio
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from pydantic import BaseModel

from src.mcp_server.db import fetch_available_doctor_slots, fetch_booked_slots, mark_slot_unbooked
from src.orchestration.graph import build_graph
from src.state.models import AgentState

app = FastAPI(title="Hospital AI Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

graph_app = build_graph()


class QueryRequest(BaseModel):
    message: str


class ResumeRequest(BaseModel):
    thread_id: str
    slot_id: int


def _choose_slot_response(thread_id: str, state: dict, payload: dict) -> dict:
    triage = state["triage"]
    redacted = state["redacted_input"]
    return {
        "status": "choose_slot",
        "thread_id": thread_id,
        "symptoms": redacted.stated_symptoms,
        "stated_need": redacted.stated_need,
        "urgency": triage.urgency.value,
        "rationale": triage.rationale,
        "required_specialization": payload["required_specialization"],
        "available_slots": payload["available_slots"],
        "recommended_slot_id": payload["recommended_slot_id"],
        "reasoning": payload["reasoning"],
    }


async def _run_until_patient_decision(config: dict, state) -> dict:
    result = await graph_app.ainvoke(state, config=config)
    snapshot = await graph_app.aget_state(config)

    while snapshot.next:
        payload = snapshot.tasks[0].interrupts[0].value
        reason = payload.get("reason")

        if reason == "escalate_to_human":
            print("\n[HUMAN REVIEW NEEDED]")
            print("  urgency:", payload.get("urgency"))
            print("  rationale:", payload.get("rationale"))
            answer = await asyncio.to_thread(
                input, payload.get("prompt", "Decision: ") + " "
            )
            result = await graph_app.ainvoke(Command(resume=answer), config=config)
            snapshot = await graph_app.aget_state(config)
            continue

        if reason == "choose_slot":
            return _choose_slot_response(config["configurable"]["thread_id"], result, payload)

        if reason == "no_slots":
            result = await graph_app.ainvoke(Command(resume=None), config=config)
            return {
                "status": "no_slots",
                "required_specialization": payload.get("required_specialization"),
            }

        raise RuntimeError(f"Unhandled interrupt reason: {reason}")

    if result.get("blocked"):
        return {"status": "blocked", "reason": result.get("block_reason")}

    if result.get("emergency_message"):
        return {"status": "emergency", "message": result["emergency_message"]}

    raise RuntimeError("Graph finished without reaching a known terminal state.")


@app.post("/api/query")
async def submit_query(body: QueryRequest) -> dict:
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        return await _run_until_patient_decision(config, AgentState(raw_message=body.message))
    except Exception as exc:  # noqa: BLE001 - surface the real cause to the frontend
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/resume")
async def resume_with_slot(body: ResumeRequest) -> dict:
    config = {"configurable": {"thread_id": body.thread_id}}

    try:
        result = await graph_app.ainvoke(Command(resume=body.slot_id), config=config)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    outcome = result.get("scheduling_result")
    if outcome is None or not outcome.booked:
        raise HTTPException(status_code=500, detail="Booking did not complete.")

    return {"status": "booked", "slot_id": outcome.booked_slot_id}


@app.get("/api/appointments")
async def list_appointments() -> dict:
    return {"appointments": fetch_booked_slots()}


@app.delete("/api/appointments/{slot_id}")
async def cancel_appointment(slot_id: int) -> dict:
    cancelled = mark_slot_unbooked(slot_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Appointment not found or already cancelled.")
    return {"status": "cancelled", "slot_id": slot_id}


@app.get("/api/available-slots")
async def available_slots() -> dict:
    return {"available_slots": fetch_available_doctor_slots()}
