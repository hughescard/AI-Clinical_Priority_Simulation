from __future__ import annotations

import heapq
from itertools import count

from app.algorithms.base import PlanningAlgorithm, PlanningState
from app.models.patient import Patient
from app.planning.costs import (
    calculate_incremental_cost,
    calculate_terminal_remaining_cost,
    preliminary_priority_score,
)
from app.planning.heuristics import estimate_remaining_cost
from app.planning.state import SearchPlanningState


class AStarPlanningAlgorithm(PlanningAlgorithm):
    name = "astar"

    def __init__(self, planning_window_size: int = 8) -> None:
        self.planning_window_size = planning_window_size

    def planning_time_penalty_minutes(self) -> float:
        return round(1.0 * (self.planning_window_size / 8.0), 3)

    def plan(self, state: PlanningState) -> list[Patient]:
        preliminary_order = sorted(
            state.waiting_patients,
            key=lambda patient: (
                -preliminary_priority_score(patient),
                patient.arrival_time,
                patient.patient_id,
            ),
        )
        candidate_patients = preliminary_order[: self.planning_window_size]
        trailing_patients = preliminary_order[self.planning_window_size :]
        patients_by_id = {patient.patient_id: patient for patient in candidate_patients}

        search_state = SearchPlanningState.initial(
            current_time=state.current_time,
            candidate_patients=candidate_patients,
            available_resources=state.resource_availability,
        )
        best_prefix_ids = self._run_search(search_state, patients_by_id)
        prefix_patients = [patients_by_id[patient_id] for patient_id in best_prefix_ids]
        selected_patient_ids = set(best_prefix_ids)
        remaining_patients = [patient for patient in preliminary_order if patient.patient_id not in selected_patient_ids]
        return prefix_patients + remaining_patients + [
            patient for patient in state.waiting_patients if patient.patient_id not in {p.patient_id for p in preliminary_order}
        ]

    def _run_search(
        self,
        initial_state: SearchPlanningState,
        patients_by_id: dict[str, Patient],
    ) -> tuple[str, ...]:
        frontier: list[tuple[float, float, int, SearchPlanningState]] = []
        tie_breaker = count()
        initial_estimate = estimate_remaining_cost(initial_state, patients_by_id)
        heapq.heappush(
            frontier,
            (initial_state.accumulated_cost + initial_estimate, initial_state.accumulated_cost, next(tie_breaker), initial_state),
        )
        best_cost_by_signature: dict[tuple, float] = {}
        best_terminal_cost = float("inf")
        best_terminal_ids: tuple[str, ...] = ()

        while frontier:
            estimated_total, _, _, current_state = heapq.heappop(frontier)
            if estimated_total >= best_terminal_cost:
                continue
            signature = current_state.signature
            known_cost = best_cost_by_signature.get(signature)
            if known_cost is not None and known_cost <= current_state.accumulated_cost:
                continue
            best_cost_by_signature[signature] = current_state.accumulated_cost

            selectable_ids = [
                patient_id
                for patient_id in current_state.remaining_patient_ids
                if current_state.can_assign(patients_by_id[patient_id])
            ]
            if not selectable_ids:
                terminal_cost = current_state.accumulated_cost + calculate_terminal_remaining_cost(
                    [patients_by_id[patient_id] for patient_id in current_state.remaining_patient_ids],
                    current_time=current_state.current_time,
                    projected_time=current_state.projected_time,
                )
                if terminal_cost < best_terminal_cost or (
                    terminal_cost == best_terminal_cost and current_state.ordered_patient_ids < best_terminal_ids
                ):
                    best_terminal_cost = terminal_cost
                    best_terminal_ids = current_state.ordered_patient_ids
                continue

            ordered_selectable_ids = sorted(
                selectable_ids,
                key=lambda patient_id: (
                    -preliminary_priority_score(patients_by_id[patient_id]),
                    patients_by_id[patient_id].arrival_time,
                    patient_id,
                ),
            )
            for patient_id in ordered_selectable_ids:
                patient = patients_by_id[patient_id]
                incremental_cost = calculate_incremental_cost(
                    patient,
                    current_time=current_state.current_time,
                    projected_time=current_state.projected_time,
                )
                next_state = current_state.select(patient, incremental_cost)
                estimated_cost = next_state.accumulated_cost + estimate_remaining_cost(next_state, patients_by_id)
                if estimated_cost >= best_terminal_cost:
                    continue
                heapq.heappush(
                    frontier,
                    (estimated_cost, next_state.accumulated_cost, next(tie_breaker), next_state),
                )

        return best_terminal_ids
