from __future__ import annotations

import random

from app.data.schemas import DatasetPatientRecord
from app.models.patient import Patient


def map_external_acuity_to_risk(structured_acuity: int | None) -> int | None:
    if structured_acuity is None:
        return None
    return max(1, min(5, 6 - structured_acuity))


def infer_risk_level(record: DatasetPatientRecord) -> int:
    mapped = map_external_acuity_to_risk(record.structured_acuity)
    if mapped is not None:
        return mapped
    complaint = record.chief_complaint.lower()
    if any(keyword in complaint for keyword in ("cardiac arrest", "chest pain", "severe bleeding", "dyspnea")):
        return 4
    if record.heart_rate and record.heart_rate >= 130:
        return 4
    if record.oxygen_saturation and record.oxygen_saturation < 90:
        return 5
    if record.systolic_bp and record.systolic_bp < 90:
        return 5
    if record.temperature and record.temperature >= 39.5:
        return 3
    return 2


def build_clinical_description(record: DatasetPatientRecord) -> str:
    details = [record.clinical_description.strip()]
    for label, value in (
        ("temperature", record.temperature),
        ("heart rate", record.heart_rate),
        ("respiratory rate", record.respiratory_rate),
        ("oxygen saturation", record.oxygen_saturation),
        ("systolic bp", record.systolic_bp),
        ("diastolic bp", record.diastolic_bp),
        ("pain", record.pain),
    ):
        if value is not None and str(value).strip() != "":
            details.append(f"{label}: {value}")
    return "; ".join(dict.fromkeys(part for part in details if part))


def convert_record_to_patient(
    record: DatasetPatientRecord,
    *,
    seed: int,
    index: int,
    fallback_arrival_time: int,
) -> Patient:
    randomizer = random.Random(f"{seed}:{record.external_id}:{index}")
    risk_level = infer_risk_level(record)
    age = record.age if record.age is not None else randomizer.randint(18, 89)
    arrival_time = float(record.arrival_time if record.arrival_time is not None else fallback_arrival_time)
    return Patient(
        patient_id=record.external_id,
        age=age,
        arrival_time=arrival_time,
        chief_complaint=record.chief_complaint,
        clinical_description=build_clinical_description(record),
        risk_level=risk_level,
        current_risk=float(risk_level),
        deterioration_rate=0.0,
        max_wait_time={5: 0, 4: 10, 3: 30, 2: 60, 1: 120}[risk_level],
        estimated_service_time=30,
        required_resources=[],
    )

