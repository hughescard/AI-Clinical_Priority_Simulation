from app.data.normalization import convert_record_to_patient, infer_risk_level, map_external_acuity_to_risk
from app.data.schemas import DatasetPatientRecord


def test_acuity_mapping_is_correct() -> None:
    assert map_external_acuity_to_risk(1) == 5
    assert map_external_acuity_to_risk(5) == 1
    assert map_external_acuity_to_risk(3) == 3


def test_dataset_record_normalizes_to_patient() -> None:
    record = DatasetPatientRecord(
        external_id="ext-1",
        age=44,
        arrival_time=None,
        chief_complaint="Chest pain",
        clinical_description="Chest pain and diaphoresis",
        structured_acuity=2,
        heart_rate=118,
        oxygen_saturation=95,
        source_dataset="mimic_iv_ed",
    )
    patient = convert_record_to_patient(record, seed=42, index=0, fallback_arrival_time=7)
    assert patient.patient_id == "ext-1"
    assert patient.age == 44
    assert patient.arrival_time == 7
    assert patient.risk_level == 4


def test_infer_risk_from_vitals_when_acuity_missing() -> None:
    record = DatasetPatientRecord(
        external_id="ext-2",
        age=None,
        arrival_time=None,
        chief_complaint="Shortness of breath",
        clinical_description="Dyspnea with low oxygen saturation",
        structured_acuity=None,
        oxygen_saturation=88.0,
        source_dataset="mietic",
    )
    assert infer_risk_level(record) == 4 or infer_risk_level(record) == 5
