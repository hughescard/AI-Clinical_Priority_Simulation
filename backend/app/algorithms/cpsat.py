from __future__ import annotations

from ortools.sat.python import cp_model

from app.algorithms.base import PlanningAlgorithm, PlanningState
from app.algorithms.greedy import DynamicGreedyPlanningAlgorithm
from app.models.patient import Patient
from app.planning.costs import preliminary_priority_score


class CPSATPlanningAlgorithm(PlanningAlgorithm):
    name = "cpsat"

    def __init__(self, planning_window_size: int = 10) -> None:
        self.planning_window_size = planning_window_size
        self._greedy_fallback = DynamicGreedyPlanningAlgorithm()

    def planning_time_penalty_minutes(self) -> float:
        return round(1.5 * (self.planning_window_size / 10.0), 3)

    def plan(self, state: PlanningState) -> list[Patient]:
        greedy_order = self._greedy_fallback.plan(state)
        candidate_patients = greedy_order[: self.planning_window_size]
        if not candidate_patients:
            return greedy_order

        selected_patients = self._optimize_batch(candidate_patients, state.resource_availability)
        if not selected_patients:
            return greedy_order

        selected_ids = {patient.patient_id for patient in selected_patients}
        remaining = [patient for patient in greedy_order if patient.patient_id not in selected_ids]
        return selected_patients + remaining

    def _optimize_batch(
        self,
        candidate_patients: list[Patient],
        resource_availability: dict[str, int],
    ) -> list[Patient]:
        model = cp_model.CpModel()
        select_vars = {
            patient.patient_id: model.NewBoolVar(f"select_{patient.patient_id}")
            for patient in candidate_patients
        }

        for resource_name, capacity in resource_availability.items():
            coefficients = []
            variables = []
            for patient in candidate_patients:
                required = patient.required_resources.count(resource_name)
                if required > 0:
                    variables.append(select_vars[patient.patient_id])
                    coefficients.append(required)
            if variables:
                model.Add(sum(variable * coefficient for variable, coefficient in zip(variables, coefficients)) <= capacity)

        utilities: dict[str, int] = {}
        for patient in candidate_patients:
            utilities[patient.patient_id] = _scaled_utility(patient)

        model.Maximize(sum(select_vars[patient.patient_id] * utilities[patient.patient_id] for patient in candidate_patients))

        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 0
        solver.parameters.max_time_in_seconds = 1.0

        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return []

        selected = [
            patient
            for patient in candidate_patients
            if solver.Value(select_vars[patient.patient_id]) == 1
        ]
        if not selected:
            return []

        return sorted(
            selected,
            key=lambda patient: (
                -utilities[patient.patient_id],
                -preliminary_priority_score(patient),
                patient.arrival_time,
                patient.patient_id,
            ),
        )


def _scaled_utility(patient: Patient) -> int:
    overdue = max(0.0, patient.waiting_time - patient.max_wait_time)
    utility = (
        patient.current_risk * 22.0
        + patient.waiting_time * 1.2
        + overdue * 18.0
        + patient.deterioration_rate * 140.0
        + (65.0 if patient.risk_level == 5 else 0.0)
        - len(patient.required_resources) * 3.0
        - patient.estimated_service_time * 0.4
    )
    return max(1, int(round(utility * 100)))
