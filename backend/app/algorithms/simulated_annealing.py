from __future__ import annotations

import math
import random

from app.algorithms.base import PlanningAlgorithm, PlanningState
from app.algorithms.greedy import DynamicGreedyPlanningAlgorithm
from app.models.patient import Patient
from app.planning.costs import preliminary_priority_score


class SimulatedAnnealingPlanningAlgorithm(PlanningAlgorithm):
    name = "simulated_annealing"

    def __init__(
        self,
        *,
        top_k: int = 10,
        max_iterations: int = 120,
        initial_temperature: float = 1.0,
        cooling_rate: float = 0.95,
        min_temperature: float = 0.01,
        planning_overhead_minutes: float = 1.5,
    ) -> None:
        self.top_k = top_k
        self.max_iterations = max_iterations
        self.initial_temperature = initial_temperature
        self.cooling_rate = cooling_rate
        self.min_temperature = min_temperature
        self._planning_overhead_minutes = planning_overhead_minutes
        self._greedy = DynamicGreedyPlanningAlgorithm()

    def planning_time_penalty_minutes(self) -> float:
        return self._planning_overhead_minutes

    def plan(self, state: PlanningState) -> list[Patient]:
        base_order = self.initial_candidate_order(state)
        candidate_patients = base_order[: self.top_k]
        if len(candidate_patients) <= 1:
            return base_order

        rng = random.Random(self._build_seed(state, candidate_patients))
        current_order = list(candidate_patients)
        current_cost = self._objective(current_order, state)
        best_order = list(current_order)
        best_cost = current_cost
        temperature = self.initial_temperature

        for iteration in range(self.max_iterations):
            if temperature < self.min_temperature:
                break
            neighbor = self._generate_neighbor(current_order, rng, iteration)
            neighbor_cost = self._objective(neighbor, state)
            delta = neighbor_cost - current_cost
            if delta < 0 or self._should_accept_worse(delta, temperature, rng):
                current_order = neighbor
                current_cost = neighbor_cost
            if self._is_better_solution(current_order, current_cost, best_order, best_cost):
                best_order = list(current_order)
                best_cost = current_cost
            temperature *= self.cooling_rate

        selected_ids = {patient.patient_id for patient in best_order}
        remaining_patients = [patient for patient in base_order if patient.patient_id not in selected_ids]
        return best_order + remaining_patients

    def _build_seed(self, state: PlanningState, candidate_patients: list[Patient]) -> int:
        patient_signature = sum(
            (index + 1) * sum(ord(char) for char in patient.patient_id)
            for index, patient in enumerate(candidate_patients)
        )
        return int(state.random_seed * 10_007 + round(state.current_time * 100) + patient_signature)

    def _generate_neighbor(
        self,
        ordered_patients: list[Patient],
        rng: random.Random,
        iteration: int,
    ) -> list[Patient]:
        neighbor = list(ordered_patients)
        if len(neighbor) < 2:
            return neighbor

        move_type = iteration % 3
        left_index = rng.randrange(len(neighbor))
        right_index = rng.randrange(len(neighbor))
        while right_index == left_index and len(neighbor) > 1:
            right_index = rng.randrange(len(neighbor))
        if left_index > right_index:
            left_index, right_index = right_index, left_index

        if move_type == 0:
            neighbor[left_index], neighbor[right_index] = neighbor[right_index], neighbor[left_index]
        elif move_type == 1:
            patient = neighbor.pop(left_index)
            neighbor.insert(right_index, patient)
        else:
            segment_end = min(len(neighbor), right_index + 2)
            neighbor[left_index:segment_end] = reversed(neighbor[left_index:segment_end])
        return neighbor

    def _objective(self, ordered_patients: list[Patient], state: PlanningState) -> float:
        available_resources = dict(state.resource_availability)
        projected_time = state.current_time
        total_cost = 0.0
        total_patients = len(ordered_patients)

        for position, patient in enumerate(ordered_patients):
            priority_weight = position + 1
            scheduling_delay = max(0.0, projected_time - state.current_time)
            total_wait = patient.waiting_time + scheduling_delay
            overdue = max(0.0, total_wait - patient.max_wait_time)
            textual_risk = float(patient.textual_risk_score or patient.risk_level)
            urgency_penalty = (
                patient.current_risk * 7.5
                + textual_risk * 4.5
                + total_wait * 0.8
                + patient.deterioration_rate * 60.0
                + overdue * (18.0 + patient.current_risk * 2.0)
            )
            critical_penalty = 0.0
            if patient.risk_level >= 4:
                critical_penalty += priority_weight * 12.0
            if patient.risk_level == 5 and position > 0:
                critical_penalty += 120.0 + overdue * 10.0

            feasible = self._can_allocate(patient, available_resources)
            infeasible_front_penalty = 0.0
            if not feasible:
                front_pressure = max(1, total_patients - position)
                infeasible_front_penalty = front_pressure * (
                    35.0
                    + len(patient.required_resources) * 5.0
                    + overdue * 2.5
                )
                if patient.risk_level >= 4:
                    infeasible_front_penalty *= 0.85
            else:
                self._allocate(patient, available_resources)

            tie_break_penalty = self._stable_tie_break_penalty(patient)
            total_cost += (
                priority_weight * urgency_penalty
                + critical_penalty
                + infeasible_front_penalty
                + len(patient.required_resources) * 1.25
                + patient.estimated_service_time * 0.12
                + tie_break_penalty
            )
            projected_time += patient.estimated_service_time

        return round(total_cost, 6)

    def _can_allocate(self, patient: Patient, available_resources: dict[str, int]) -> bool:
        requirements: dict[str, int] = {}
        for resource in patient.required_resources:
            requirements[resource] = requirements.get(resource, 0) + 1
        return all(available_resources.get(resource, 0) >= amount for resource, amount in requirements.items())

    def _allocate(self, patient: Patient, available_resources: dict[str, int]) -> None:
        for resource in patient.required_resources:
            available_resources[resource] = available_resources.get(resource, 0) - 1

    def _should_accept_worse(self, delta: float, temperature: float, rng: random.Random) -> bool:
        if temperature <= 0:
            return False
        acceptance_probability = math.exp(-delta / max(temperature, 1e-9))
        return rng.random() < acceptance_probability

    def _is_better_solution(
        self,
        current_order: list[Patient],
        current_cost: float,
        best_order: list[Patient],
        best_cost: float,
    ) -> bool:
        if current_cost < best_cost:
            return True
        if current_cost > best_cost:
            return False
        current_ids = tuple(patient.patient_id for patient in current_order)
        best_ids = tuple(patient.patient_id for patient in best_order)
        return current_ids < best_ids

    def _stable_tie_break_penalty(self, patient: Patient) -> float:
        return patient.arrival_time * 0.001 + sum(ord(char) for char in patient.patient_id) * 0.00001

    def initial_candidate_order(self, state: PlanningState) -> list[Patient]:
        try:
            return self._greedy.plan(state)
        except Exception:
            return sorted(
                state.waiting_patients,
                key=lambda patient: (
                    -patient.current_risk,
                    -(patient.textual_risk_score or patient.risk_level),
                    patient.arrival_time,
                    patient.patient_id,
                ),
            )

    def preliminary_priority(self, patient: Patient) -> float:
        return preliminary_priority_score(patient)
