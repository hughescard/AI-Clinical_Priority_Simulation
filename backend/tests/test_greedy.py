from app.algorithms.base import PlanningState
from app.algorithms.greedy import DynamicGreedyPlanningAlgorithm
from app.models.patient import Patient


def build_patient(
    patient_id: str,
    *,
    arrival_time: int,
    current_risk: float,
    deterioration_rate: float,
    max_wait_time: int,
    required_resources: list[str],
) -> Patient:
    patient = Patient(
        patient_id=patient_id,
        age=50,
        arrival_time=arrival_time,
        chief_complaint="Dyspnea",
        clinical_description="Test patient",
        risk_level=4,
        current_risk=current_risk,
        deterioration_rate=deterioration_rate,
        max_wait_time=max_wait_time,
        estimated_service_time=25,
        required_resources=required_resources,
    )
    patient.update_waiting_time(40)
    return patient


def test_greedy_prioritizes_more_critical_patient() -> None:
    algorithm = DynamicGreedyPlanningAlgorithm()
    state = PlanningState(
        current_time=40,
        waiting_patients=[
            build_patient(
                "stable",
                arrival_time=10,
                current_risk=3.0,
                deterioration_rate=0.03,
                max_wait_time=60,
                required_resources=["doctor"],
            ),
            build_patient(
                "critical",
                arrival_time=20,
                current_risk=5.5,
                deterioration_rate=0.09,
                max_wait_time=10,
                required_resources=["doctor", "nurse"],
            ),
        ],
        resource_availability={"doctor": 1, "nurse": 1},
    )
    ordered = algorithm.plan(state)
    assert ordered[0].patient_id == "critical"

