from __future__ import annotations

from app.algorithms.base import PlanningAlgorithm, PlanningState
from app.models.patient import Patient


class FIFOPlanningAlgorithm(PlanningAlgorithm):
    name = "fifo"

    def plan(self, state: PlanningState) -> list[Patient]:
        return sorted(
            state.waiting_patients,
            key=lambda patient: (patient.arrival_time, patient.patient_id),
        )

    def planning_time_penalty_minutes(self) -> float:
        return 0.1
