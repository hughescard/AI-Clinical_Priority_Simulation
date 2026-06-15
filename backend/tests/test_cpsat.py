from app.algorithms.base import PlanningState
from app.algorithms.cpsat import CPSATPlanningAlgorithm
from app.models.patient import Patient


def build_patient(
    patient_id: str,
    *,
    arrival_time: float,
    risk_level: int,
    current_risk: float,
    deterioration_rate: float,
    max_wait_time: int,
    estimated_service_time: int,
    required_resources: list[str],
) -> Patient:
    patient = Patient(
        patient_id=patient_id,
        age=50,
        arrival_time=arrival_time,
        chief_complaint="Synthetic",
        clinical_description="Synthetic case",
        risk_level=risk_level,
        current_risk=current_risk,
        deterioration_rate=deterioration_rate,
        max_wait_time=max_wait_time,
        estimated_service_time=estimated_service_time,
        required_resources=required_resources,
    )
    patient.update_waiting_time(60)
    return patient


def test_cpsat_prioritizes_overdue_critical_patient() -> None:
    algorithm = CPSATPlanningAlgorithm(planning_window_size=4)
    critical = build_patient(
        "critical",
        arrival_time=0,
        risk_level=5,
        current_risk=5.0,
        deterioration_rate=0.12,
        max_wait_time=0,
        estimated_service_time=35,
        required_resources=["doctor", "nurse", "resuscitation_room"],
    )
    stable = build_patient(
        "stable",
        arrival_time=40,
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.02,
        max_wait_time=60,
        estimated_service_time=20,
        required_resources=["doctor"],
    )
    ordered = algorithm.plan(
        PlanningState(
            current_time=60,
            waiting_patients=[stable, critical],
            resource_availability={"doctor": 1, "nurse": 1, "resuscitation_room": 1},
        )
    )
    assert ordered[0].patient_id == "critical"


def test_cpsat_respects_resource_constraints() -> None:
    algorithm = CPSATPlanningAlgorithm(planning_window_size=4)
    heavy = build_patient(
        "heavy",
        arrival_time=0,
        risk_level=5,
        current_risk=5.0,
        deterioration_rate=0.08,
        max_wait_time=10,
        estimated_service_time=30,
        required_resources=["doctor", "doctor"],
    )
    feasible = build_patient(
        "feasible",
        arrival_time=5,
        risk_level=4,
        current_risk=4.0,
        deterioration_rate=0.05,
        max_wait_time=20,
        estimated_service_time=25,
        required_resources=["doctor"],
    )
    ordered = algorithm.plan(
        PlanningState(
            current_time=60,
            waiting_patients=[heavy, feasible],
            resource_availability={"doctor": 1},
        )
    )
    assert ordered[0].patient_id == "feasible"


def test_cpsat_returns_all_waiting_patients() -> None:
    algorithm = CPSATPlanningAlgorithm(planning_window_size=3)
    patients = [
        build_patient(
            f"P{i}",
            arrival_time=float(i),
            risk_level=2 + (i % 3),
            current_risk=2.0 + (i % 3),
            deterioration_rate=0.02 * i,
            max_wait_time=25 + i,
            estimated_service_time=10 + i,
            required_resources=["doctor"],
        )
        for i in range(1, 7)
    ]
    ordered = algorithm.plan(
        PlanningState(current_time=60, waiting_patients=patients, resource_availability={"doctor": 1})
    )
    assert len(ordered) == len(patients)
    assert {patient.patient_id for patient in ordered} == {patient.patient_id for patient in patients}


def test_cpsat_is_deterministic() -> None:
    algorithm = CPSATPlanningAlgorithm(planning_window_size=5)
    patients = [
        build_patient("P1", arrival_time=0, risk_level=3, current_risk=3.0, deterioration_rate=0.04, max_wait_time=20, estimated_service_time=30, required_resources=["doctor"]),
        build_patient("P2", arrival_time=4, risk_level=4, current_risk=4.2, deterioration_rate=0.06, max_wait_time=15, estimated_service_time=20, required_resources=["doctor", "nurse"]),
        build_patient("P3", arrival_time=9, risk_level=2, current_risk=2.4, deterioration_rate=0.03, max_wait_time=80, estimated_service_time=15, required_resources=["doctor"]),
    ]
    state = PlanningState(current_time=60, waiting_patients=patients, resource_availability={"doctor": 1, "nurse": 1})
    first = [patient.patient_id for patient in algorithm.plan(state)]
    second = [patient.patient_id for patient in algorithm.plan(state)]
    assert first == second
