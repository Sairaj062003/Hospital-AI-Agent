"""FastAPI layer exposing the LangGraph pipeline and appointment data over HTTP.

Two different kinds of pauses happen inside the graph, and this API treats
them very differently:

- human_review ("tell the patient to contact authorities?") is answered by an
  admin through the /api/admin endpoints. The patient's browser polls
  /api/review/{thread_id} until that decision arrives.
- scheduling_step's choose_slot pause IS patient-facing: the frontend shows
  the available doctors/slots and the patient picks one, which becomes a
  separate /api/resume call.

Every /api route except login and logout requires a signed-in session (see
src/security/auth.py).
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel, StringConstraints

from src.mcp_server.db import fetch_available_doctor_slots, fetch_booked_slots, mark_slot_unbooked
from src.orchestration.graph import build_graph
from src.security.auth import require_login, router as auth_router
from src.state.models import AgentState

app = FastAPI(title="Hospital AI Agent API")

app.middleware("http")(require_login)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

graph_app = build_graph()

# thread_id -> review. In memory like the graph checkpointer, so run one worker.
reviews: dict[str, dict] = {}


class QueryRequest(BaseModel):
    message: str


class ResumeRequest(BaseModel):
    thread_id: str
    slot_id: int


class AdminDecisionRequest(BaseModel):
    decision: Literal["yes", "no"]
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


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


def _register_review(thread_id: str, payload: dict) -> None:
    reviews[thread_id] = {
        "status": "pending",
        "outcome": None,
        "request": {
            "thread_id": thread_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "raw_message": payload["raw_message"],
            "full_name": payload["full_name"],
            "phone_number": payload["phone_number"],
            "urgency": payload["urgency"],
            "rationale": payload["rationale"],
        },
    }


async def _run_until_pause(config: dict, graph_input) -> dict:
    result = await graph_app.ainvoke(graph_input, config=config)
    snapshot = await graph_app.aget_state(config)
    thread_id = config["configurable"]["thread_id"]
    admin_message = result.get("admin_message")

    if snapshot.next:
        payload = snapshot.tasks[0].interrupts[0].value
        reason = payload.get("reason")

        if reason == "escalate_to_human":
            _register_review(thread_id, payload)
            return {"status": "awaiting_review", "thread_id": thread_id}

        if reason == "choose_slot":
            response = _choose_slot_response(thread_id, result, payload)
            return {**response, "admin_message": admin_message}

        raise RuntimeError(f"Unhandled interrupt reason: {reason}")

    if result.get("blocked"):
        return {"status": "blocked", "reason": result.get("block_reason")}

    if result.get("emergency_message"):
        return {"status": "emergency", "message": result["emergency_message"]}

    if result.get("faq_answer"):
        return {"status": "faq_answer", "message": result["faq_answer"]}

    if result.get("no_slots_specialization"):
        return {
            "status": "no_slots",
            "required_specialization": result["no_slots_specialization"],
            "admin_message": admin_message,
        }

    raise RuntimeError("Graph finished without reaching a known terminal state.")


@app.post("/api/query")
async def submit_query(body: QueryRequest) -> dict:
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        return await _run_until_pause(config, AgentState(raw_message=body.message))
    except Exception as exc:  # noqa: BLE001 - surface the real cause to the frontend
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/review/{thread_id}")
async def review_status(thread_id: str) -> dict:
    review = reviews.get(thread_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review request not found.")
    if review["status"] != "completed":
        return {"status": "awaiting_review", "thread_id": thread_id}
    return review["outcome"]


@app.get("/api/admin/requests")
async def list_review_requests() -> dict:
    pending = [r["request"] for r in reviews.values() if r["status"] == "pending"]
    return {"requests": pending}


@app.post("/api/admin/requests/{thread_id}/decision")
async def decide_review(thread_id: str, body: AdminDecisionRequest) -> dict:
    review = reviews.get(thread_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review request not found.")
    if review["status"] != "pending":
        raise HTTPException(status_code=409, detail="This request has already been decided.")
    # Set before the first await so a second click cannot resume the graph twice.
    review["status"] = "deciding"

    config = {"configurable": {"thread_id": thread_id}}
    resume = Command(resume={"decision": body.decision, "message": body.message})

    try:
        review["outcome"] = await _run_until_pause(config, resume)
    except Exception as exc:  # noqa: BLE001
        review["outcome"] = {
            "status": "error",
            "message": "We could not load appointment options. Please submit your request "
                       "again, or call 0223567568 if it is urgent.",
            "admin_message": body.message,
        }
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        review["status"] = "completed"

    return {"status": "decided", "thread_id": thread_id}


@app.post("/api/resume")
async def resume_with_slot(body: ResumeRequest) -> dict:
    config = {"configurable": {"thread_id": body.thread_id}}

    review = reviews.get(body.thread_id)
    if review is not None and review["status"] != "completed":
        raise HTTPException(status_code=409, detail="This request is still awaiting staff review.")

    try:
        result = await graph_app.ainvoke(Command(resume=body.slot_id), config=config)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Every matching slot was taken while the patient was choosing.
    if result.get("no_slots_specialization"):
        raise HTTPException(status_code=409, detail="That slot is no longer available.")

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


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

# Only present once the frontend is built (as in the Docker image). Must stay
# last, because the "/" mount would otherwise shadow the API routes.
if FRONTEND_DIST.is_dir():

    @app.get("/admin", include_in_schema=False)
    @app.get("/admin/", include_in_schema=False)
    async def admin_page() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")

    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
