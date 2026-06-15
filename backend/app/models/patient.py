from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PatientStatus(str, Enum):
    WAITING = "WAITING"
    IN_SERVICE = "IN_SERVICE"
    TREATED = "TREATED"
    LEFT_UNTREATED = "LEFT_UNTREATED"


class Patient(BaseModel):
    patient_id: str
    age: int = Field(ge=0)
    arrival_time: float = Field(ge=0)
    chief_complaint: str
    clinical_description: str
    risk_level: int = Field(ge=1, le=5)
    current_risk: float = Field(ge=0.0)
    deterioration_rate: float = Field(ge=0.0)
    max_wait_time: int = Field(ge=0)
    estimated_service_time: int = Field(ge=1)
    required_resources: list[str] = Field(default_factory=list)
    key_symptoms: list[str] = Field(default_factory=list)
    textual_risk_score: int | None = Field(default=None, ge=1, le=5)
    clinical_category: str | None = None
    enrichment_explanation: str | None = None
    waiting_time: float = Field(default=0, ge=0)
    status: PatientStatus = PatientStatus.WAITING
    assigned_start_time: float | None = None
    service_end_time: float | None = None

    def update_waiting_time(self, current_time: float) -> None:
        self.waiting_time = max(0, current_time - self.arrival_time)

    def apply_deterioration(self, elapsed_minutes: float) -> None:
        if self.status != PatientStatus.WAITING or elapsed_minutes <= 0:
            return
        self.current_risk = min(10.0, self.current_risk + self.deterioration_rate * elapsed_minutes)

    @property
    def exceeded_wait(self) -> bool:
        return self.waiting_time > self.max_wait_time
