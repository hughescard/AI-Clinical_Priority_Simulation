from app.llm.extractor import MockClinicalExtractor
from app.models.patient import Patient


def build_patient(chief_complaint: str, clinical_description: str) -> Patient:
    return Patient(
        patient_id="P001",
        age=50,
        arrival_time=0,
        chief_complaint=chief_complaint,
        clinical_description=clinical_description,
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=60,
        estimated_service_time=30,
        required_resources=[],
    )


def test_chest_pain_case_returns_high_risk_cardiovascular() -> None:
    extractor = MockClinicalExtractor()
    enrichment = extractor.enrich_patient(
        build_patient("Chest pain", "Chest pain with dyspnea and cold sweat")
    )
    assert enrichment.textual_risk_score >= 4
    assert enrichment.clinical_category == "cardiovascular"
    assert "laboratory" in enrichment.required_resources
    assert "vital_sign_monitor" in enrichment.required_resources


def test_mild_case_returns_low_risk_and_fewer_resources() -> None:
    extractor = MockClinicalExtractor()
    enrichment = extractor.enrich_patient(
        build_patient("Sore throat", "Mild headache and sore throat for one day")
    )
    assert enrichment.textual_risk_score == 1
    assert enrichment.clinical_category == "minor"
    assert enrichment.required_resources == ["doctor"]
    assert enrichment.explanation.strip()


def test_risk_five_case_requires_resuscitation_room() -> None:
    extractor = MockClinicalExtractor()
    enrichment = extractor.enrich_patient(
        build_patient("Collapse", "Cardiac arrest after sudden collapse")
    )
    assert enrichment.textual_risk_score == 5
    assert "resuscitation_room" in enrichment.required_resources


def test_laboratory_assigned_for_relevant_categories() -> None:
    extractor = MockClinicalExtractor()
    infectious = extractor.enrich_patient(build_patient("Fever", "Fever and cough for three days"))
    trauma = extractor.enrich_patient(build_patient("Trauma", "Trauma with severe bleeding after accident"))
    assert infectious.clinical_category == "infectious"
    assert "laboratory" in infectious.required_resources
    assert "laboratory" in trauma.required_resources


def test_mock_extractor_respects_allowed_resource_catalog() -> None:
    extractor = MockClinicalExtractor()
    enrichment = extractor.enrich_patient(
        build_patient("Chest pain", "Chest pain with dyspnea and cold sweat"),
        allowed_resources=["doctor", "nurse", "ct_scanner"],
    )

    assert enrichment.required_resources == ["doctor", "nurse"]


def test_mock_extractor_uses_optional_resources_when_clinically_relevant() -> None:
    extractor = MockClinicalExtractor()

    trauma = extractor.enrich_patient(
        build_patient("Trauma", "Head trauma after fall with confusion and suspected fracture"),
        allowed_resources=["doctor", "nurse", "ct_scanner", "xray_room", "vital_sign_monitor"],
    )
    infectious = extractor.enrich_patient(
        build_patient("Fever", "Fever and cough with contagious respiratory infection concern"),
        allowed_resources=["doctor", "nurse", "isolation_room", "laboratory"],
    )

    assert "ct_scanner" in trauma.required_resources
    assert "xray_room" in trauma.required_resources
    assert "isolation_room" in infectious.required_resources
