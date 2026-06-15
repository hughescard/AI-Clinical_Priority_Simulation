from __future__ import annotations

from app.algorithms.base import PlanningState
from app.algorithms.greedy import DynamicGreedyPlanningAlgorithm
from app.algorithms.simulated_annealing import SimulatedAnnealingPlanningAlgorithm
from app.models.patient import Patient


def build_patient(
    patient_id: str,
    *,
    arrival_time: float,
    risk_level: int,
    current_risk: float,
    waiting_time: float,
    deterioration_rate: float,
    max_wait_time: int,
    estimated_service_time: int,
    required_resources: list[str],
    textual_risk_score: int | None = None,
) -> Patient:
    return Patient(
        patient_id=patient_id,
        age=50,
        arrival_time=arrival_time,
        chief_complaint=patient_id,
        clinical_description=patient_id,
        risk_level=risk_level,
        current_risk=current_risk,
        deterioration_rate=deterioration_rate,
        max_wait_time=max_wait_time,
        estimated_service_time=estimated_service_time,
        required_resources=required_resources,
        waiting_time=waiting_time,
        textual_risk_score=textual_risk_score or risk_level,
    )


def build_state(waiting_patients: list[Patient], resource_availability: dict[str, int], *, seed: int = 42) -> PlanningState:
    return PlanningState(
        current_time=20,
        waiting_patients=waiting_patients,
        resource_availability=resource_availability,
        random_seed=seed,
    )


def test_registry_behavior_returns_all_waiting_patients_exactly_once() -> None:
    patients = [
        build_patient("P1", arrival_time=0, risk_level=5, current_risk=5.0, waiting_time=20, deterioration_rate=0.08, max_wait_time=10, estimated_service_time=30, required_resources=["doctor"]),
        build_patient("P2", arrival_time=2, risk_level=3, current_risk=3.5, waiting_time=18, deterioration_rate=0.04, max_wait_time=30, estimated_service_time=20, required_resources=["doctor"]),
        build_patient("P3", arrival_time=4, risk_level=2, current_risk=2.3, waiting_time=16, deterioration_rate=0.02, max_wait_time=60, estimated_service_time=15, required_resources=["doctor"]),
    ]
    algorithm = SimulatedAnnealingPlanningAlgorithm()

    plan = algorithm.plan(build_state(patients, {"doctor": 2}))

    assert [patient.patient_id for patient in plan] == ["P1", "P2", "P3"]


def test_simulated_annealing_is_deterministic_for_same_seed_and_inputs() -> None:
    patients = [
        build_patient("P1", arrival_time=0, risk_level=4, current_risk=4.4, waiting_time=20, deterioration_rate=0.07, max_wait_time=12, estimated_service_time=25, required_resources=["doctor"]),
        build_patient("P2", arrival_time=3, risk_level=3, current_risk=3.4, waiting_time=17, deterioration_rate=0.05, max_wait_time=25, estimated_service_time=15, required_resources=["doctor"]),
        build_patient("P3", arrival_time=5, risk_level=2, current_risk=2.5, waiting_time=15, deterioration_rate=0.03, max_wait_time=60, estimated_service_time=10, required_resources=["doctor"]),
    ]
    state = build_state(patients, {"doctor": 2}, seed=77)
    algorithm = SimulatedAnnealingPlanningAlgorithm()

    first = [patient.patient_id for patient in algorithm.plan(state)]
    second = [patient.patient_id for patient in algorithm.plan(state)]

    assert first == second


def test_simulated_annealing_can_differ_from_greedy_in_controlled_scenario() -> None:
    patients = [
        build_patient("P1", arrival_time=0, risk_level=5, current_risk=5.0, waiting_time=5, deterioration_rate=0.10, max_wait_time=60, estimated_service_time=30, required_resources=["doctor", "nurse"]),
        build_patient("P2", arrival_time=1, risk_level=4, current_risk=4.3, waiting_time=19, deterioration_rate=0.05, max_wait_time=10, estimated_service_time=10, required_resources=["doctor"]),
        build_patient("P3", arrival_time=2, risk_level=2, current_risk=2.4, waiting_time=18, deterioration_rate=0.02, max_wait_time=60, estimated_service_time=10, required_resources=["doctor"]),
    ]
    state = build_state(patients, {"doctor": 1, "nurse": 0}, seed=42)
    greedy = DynamicGreedyPlanningAlgorithm()
    annealing = SimulatedAnnealingPlanningAlgorithm()

    greedy_order = [patient.patient_id for patient in greedy.plan(state)]
    annealing_order = [patient.patient_id for patient in annealing.plan(state)]

    assert greedy_order != annealing_order
    assert annealing_order[0] == "P2"


def test_high_risk_patients_tend_to_rank_before_low_risk_patients() -> None:
    patients = [
        build_patient("P1", arrival_time=0, risk_level=5, current_risk=5.2, waiting_time=20, deterioration_rate=0.09, max_wait_time=10, estimated_service_time=20, required_resources=["doctor"]),
        build_patient("P2", arrival_time=1, risk_level=1, current_risk=1.2, waiting_time=20, deterioration_rate=0.01, max_wait_time=120, estimated_service_time=20, required_resources=["doctor"]),
    ]
    algorithm = SimulatedAnnealingPlanningAlgorithm()

    plan = algorithm.plan(build_state(patients, {"doctor": 1}))

    assert [patient.patient_id for patient in plan[:2]] == ["P1", "P2"]


def test_max_wait_violation_increases_priority_impact() -> None:
    patients = [
        build_patient("P1", arrival_time=0, risk_level=3, current_risk=3.2, waiting_time=25, deterioration_rate=0.03, max_wait_time=10, estimated_service_time=20, required_resources=["doctor"]),
        build_patient("P2", arrival_time=1, risk_level=3, current_risk=3.2, waiting_time=5, deterioration_rate=0.03, max_wait_time=30, estimated_service_time=20, required_resources=["doctor"]),
    ]
    algorithm = SimulatedAnnealingPlanningAlgorithm()

    plan = algorithm.plan(build_state(patients, {"doctor": 1}))

    assert [patient.patient_id for patient in plan[:2]] == ["P1", "P2"]


def test_infeasible_patients_are_handled_without_being_dropped() -> None:
    patients = [
        build_patient("P1", arrival_time=0, risk_level=5, current_risk=5.0, waiting_time=10, deterioration_rate=0.08, max_wait_time=20, estimated_service_time=30, required_resources=["doctor", "ct_scanner"]),
        build_patient("P2", arrival_time=1, risk_level=4, current_risk=4.0, waiting_time=15, deterioration_rate=0.04, max_wait_time=10, estimated_service_time=15, required_resources=["doctor"]),
        build_patient("P3", arrival_time=2, risk_level=2, current_risk=2.3, waiting_time=18, deterioration_rate=0.02, max_wait_time=60, estimated_service_time=10, required_resources=["doctor"]),
    ]
    algorithm = SimulatedAnnealingPlanningAlgorithm()

    plan = algorithm.plan(build_state(patients, {"doctor": 1, "ct_scanner": 0}))

    assert sorted(patient.patient_id for patient in plan) == ["P1", "P2", "P3"]
    ordered_ids = [patient.patient_id for patient in plan]
    assert ordered_ids.index("P2") < ordered_ids.index("P1")
