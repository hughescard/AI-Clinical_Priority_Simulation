from __future__ import annotations

from app.models.patient import Patient
from app.planning.state import SearchPlanningState


def estimate_remaining_cost(
    state: SearchPlanningState,
    patients_by_id: dict[str, Patient],
) -> float:
    if not state.remaining_patient_ids:
        return 0.0
    min_service_time = min(
        patients_by_id[patient_id].estimated_service_time for patient_id in state.remaining_patient_ids
    )
    estimated_cost = 0.0
    for index, patient_id in enumerate(state.remaining_patient_ids):
        patient = patients_by_id[patient_id]
        relaxed_delay = index * min_service_time
        total_wait = patient.waiting_time + relaxed_delay
        overdue = max(0, total_wait - patient.max_wait_time)
        estimated_cost += patient.current_risk * (1.0 + relaxed_delay / 30.0)
        estimated_cost += patient.deterioration_rate * 15.0
        estimated_cost += overdue * (5.0 + patient.current_risk)
        if patient.risk_level == 5:
            estimated_cost += 40.0
    return round(estimated_cost, 6)

