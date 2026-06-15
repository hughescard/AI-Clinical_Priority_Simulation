from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    PATIENT_ARRIVAL = "PATIENT_ARRIVAL"
    INITIAL_ASSESSMENT = "INITIAL_ASSESSMENT"
    DISPATCH_ATTEMPT = "DISPATCH_ATTEMPT"
    SERVICE_START = "SERVICE_START"
    SERVICE_END = "SERVICE_END"
    DETERIORATION_UPDATE = "DETERIORATION_UPDATE"
    DOCTOR_ROUND_START = "DOCTOR_ROUND_START"
    DOCTOR_ROUND_END = "DOCTOR_ROUND_END"
    DOCTOR_ROUND_IDLE_CHECK = "DOCTOR_ROUND_IDLE_CHECK"


class Event(BaseModel):
    time: float = Field(ge=0)
    priority: int = 0
    event_type: EventType
    patient_id: str | None = None
    payload: dict = Field(default_factory=dict)
