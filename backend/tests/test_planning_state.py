from app.models.patient import Patient
from app.planning.state import SearchPlanningState


def build_patient(patient_id: str, required_resources: list[str], estimated_service_time: int = 20) -> Patient:
    return Patient(
        patient_id=patient_id,
        age=40,
        arrival_time=0,
        chief_complaint="Test",
        clinical_description="Test patient",
        risk_level=3,
        current_risk=3.0,
        deterioration_rate=0.05,
        max_wait_time=30,
        estimated_service_time=estimated_service_time,
        required_resources=required_resources,
    )


def test_search_planning_state_is_copy_safe_on_select() -> None:
    patient = build_patient("P1", ["doctor", "nurse"], estimated_service_time=25)
    state = SearchPlanningState.initial(
        current_time=10,
        candidate_patients=[patient],
        available_resources={"doctor": 1, "nurse": 1},
    )

    next_state = state.select(patient, incremental_cost=12.5)

    assert state.ordered_patient_ids == ()
    assert next_state.ordered_patient_ids == ("P1",)
    assert next_state.projected_time == 35
    assert next_state.available_resources_map == {"doctor": 0, "nurse": 0}


def test_search_planning_state_checks_resource_feasibility() -> None:
    patient = build_patient("P2", ["doctor", "observation_bed"])
    state = SearchPlanningState.initial(
        current_time=5,
        candidate_patients=[patient],
        available_resources={"doctor": 1, "observation_bed": 0},
    )
    assert state.can_assign(patient) is False

