from app.algorithms.base import PlanningState
from app.algorithms.fifo import FIFOPlanningAlgorithm
from app.models.patient import Patient


def build_patient(patient_id: str, arrival_time: int) -> Patient:
    return Patient(
        patient_id=patient_id,
        age=40,
        arrival_time=arrival_time,
        chief_complaint="Fever",
        clinical_description="Test patient",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.05,
        max_wait_time=60,
        estimated_service_time=30,
        required_resources=["doctor"],
    )


def test_fifo_orders_by_arrival_time() -> None:
    algorithm = FIFOPlanningAlgorithm()
    state = PlanningState(
        current_time=20,
        waiting_patients=[
            build_patient("P3", 15),
            build_patient("P1", 5),
            build_patient("P2", 10),
        ],
        resource_availability={"doctor": 1},
    )
    ordered = algorithm.plan(state)
    assert [patient.patient_id for patient in ordered] == ["P1", "P2", "P3"]

