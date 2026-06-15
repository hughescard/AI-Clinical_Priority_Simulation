from __future__ import annotations

from app.models.patient import Patient


def preliminary_priority_score(patient: Patient) -> float:
    total_wait = patient.waiting_time
    overdue = max(0, total_wait - patient.max_wait_time)
    return (
        patient.current_risk * 8.0
        + patient.deterioration_rate * 25.0
        + total_wait * 0.4
        + overdue * 4.0
        - len(patient.required_resources) * 0.75
        - patient.estimated_service_time * 0.05
    )


def calculate_incremental_cost(patient: Patient, current_time: int, projected_time: int) -> float:
    scheduling_delay = max(0, projected_time - current_time)
    total_wait = patient.waiting_time + scheduling_delay
    overdue = max(0, total_wait - patient.max_wait_time)
    risk_penalty = patient.current_risk * (2.0 + total_wait / 12.0)
    deterioration_penalty = patient.deterioration_rate * (20.0 + total_wait * 1.5)
    overdue_penalty = overdue * (10.0 + patient.current_risk * 2.5)
    critical_penalty = 80.0 if patient.risk_level == 5 and total_wait > 0 else 0.0
    service_penalty = patient.estimated_service_time * 0.08
    resource_penalty = len(patient.required_resources) * 0.5
    return round(
        risk_penalty
        + deterioration_penalty
        + overdue_penalty
        + critical_penalty
        + service_penalty
        + resource_penalty,
        6,
    )


def calculate_terminal_remaining_cost(
    remaining_patients: list[Patient],
    *,
    current_time: int,
    projected_time: int,
) -> float:
    penalty = 0.0
    for patient in remaining_patients:
        scheduling_delay = max(0, projected_time - current_time)
        total_wait = patient.waiting_time + scheduling_delay
        overdue = max(0, total_wait - patient.max_wait_time)
        penalty += patient.current_risk * 6.0
        penalty += patient.deterioration_rate * 30.0
        penalty += overdue * (8.0 + patient.current_risk * 2.0)
        if patient.risk_level >= 4:
            penalty += 25.0
        if patient.risk_level == 5:
            penalty += 120.0
    return round(penalty, 6)

