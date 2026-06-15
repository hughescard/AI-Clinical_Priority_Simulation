from __future__ import annotations

from app.algorithms.base import PlanningAlgorithm, PlanningState
from app.models.patient import Patient


class DynamicGreedyPlanningAlgorithm(PlanningAlgorithm):
    name = "greedy"

    def plan(self, state: PlanningState) -> list[Patient]:
        return sorted(
            state.waiting_patients,
            key=lambda patient: (-self._priority(patient), patient.arrival_time, patient.patient_id),
        )

    def _priority(self, patient: Patient) -> float:
        resource_cost = max(1, len(patient.required_resources))
        wait_penalty = 25.0 if patient.exceeded_wait else 0.0
        return (
            patient.current_risk * 6.0
            + patient.waiting_time * 0.35
            + wait_penalty
            + patient.deterioration_rate * 8.0
            - resource_cost * 1.5
        )

    def planning_time_penalty_minutes(self) -> float:
        return 0.3
