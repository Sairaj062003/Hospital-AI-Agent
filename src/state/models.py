from enum import Enum
from typing import Optional

from pydantic import BaseModel


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class PatientContact(BaseModel):
    """Real PII. Only the scheduling/booking tool should ever read this."""

    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None


class RedactedPatientInput(BaseModel):
    """What Intake/Triage reason over. No direct identifiers."""

    raw_message_redacted: str
    stated_symptoms: list[str] = []
    stated_need: Optional[str] = None


class TriageResult(BaseModel):
    urgency: UrgencyLevel
    escalate_to_human: bool
    rationale: str


class SchedulingRecommendation(BaseModel):
    recommended_slot_id: str
    reasoning: str


class SchedulingOutcome(BaseModel):
    recommendation: SchedulingRecommendation
    requires_approval: bool
    booked: bool
    booked_slot_id: Optional[str] = None


class AgentState(BaseModel):
    raw_message: str
    contact: Optional[PatientContact] = None
    redacted_input: Optional[RedactedPatientInput] = None
    triage: Optional[TriageResult] = None
    scheduling_result: Optional[SchedulingOutcome] = None