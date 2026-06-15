from __future__ import annotations

from pydantic import BaseModel, Field


class DatasetPatientRecord(BaseModel):
    external_id: str
    age: int | None = Field(default=None, ge=0)
    arrival_time: int | None = Field(default=None, ge=0)
    chief_complaint: str
    clinical_description: str
    structured_acuity: int | None = Field(default=None, ge=1, le=5)
    temperature: float | None = None
    heart_rate: float | None = None
    respiratory_rate: float | None = None
    oxygen_saturation: float | None = None
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    pain: str | float | None = None
    source_dataset: str

