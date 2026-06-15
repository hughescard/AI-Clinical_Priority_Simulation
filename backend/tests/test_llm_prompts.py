from __future__ import annotations

import pytest

from app.llm.extractor import LLMExtractionError, MockClinicalExtractor
from app.llm.ollama_extractor import OllamaClinicalExtractor
from app.llm.prompts import (
    CLINICAL_ENRICHMENT_JSON_TEMPLATE,
    build_structured_output_retry_prompt,
    build_system_prompt,
    extract_active_resource_ids,
)
from app.llm.schemas import ClinicalEnrichment
from app.models.patient import Patient
from app.models.simulation import ResourceCatalogEntry


def build_patient(description: str) -> Patient:
    return Patient(
        patient_id="P001",
        age=39,
        arrival_time=0,
        chief_complaint="Trauma",
        clinical_description=description,
        risk_level=3,
        current_risk=3.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=30,
        required_resources=[],
    )


def build_catalog() -> dict[str, ResourceCatalogEntry]:
    return {
        "doctor": ResourceCatalogEntry(id="doctor", capacity=2, enabled=True),
        "nurse": ResourceCatalogEntry(id="nurse", capacity=2, enabled=True),
        "ct_scanner": ResourceCatalogEntry(id="ct_scanner", capacity=1, enabled=True),
        "xray_room": ResourceCatalogEntry(id="xray_room", capacity=1, enabled=True),
        "isolation_room": ResourceCatalogEntry(id="isolation_room", capacity=1, enabled=True),
    }


def test_system_prompt_includes_active_resource_catalog_and_optional_guidance() -> None:
    prompt = build_system_prompt(
        ["doctor", "nurse", "ct_scanner", "xray_room", "isolation_room"],
        active_resource_catalog=build_catalog(),
    )

    assert "Available active resources" in prompt
    assert "ct_scanner: enabled=True, capacity=1" in prompt
    assert "xray_room: enabled=True, capacity=1" in prompt
    assert "Neurological symptoms, stroke-like symptoms, seizure" in prompt
    assert "Include optional resources when clinically relevant" in prompt


def test_system_prompt_includes_enabled_zero_capacity_resource() -> None:
    prompt = build_system_prompt(
        ["doctor", "ct_scanner"],
        active_resource_catalog={
            "doctor": ResourceCatalogEntry(id="doctor", capacity=2, enabled=True),
            "ct_scanner": ResourceCatalogEntry(id="ct_scanner", capacity=0, enabled=True),
            "xray_room": ResourceCatalogEntry(id="xray_room", capacity=0, enabled=False),
        },
    )

    assert "ct_scanner: enabled=True, capacity=0" in prompt
    assert "currently unavailable / zero capacity" in prompt
    assert "- xray_room: enabled=" not in prompt


def test_retry_prompt_includes_active_resource_catalog_and_id_only_instruction() -> None:
    prompt = build_structured_output_retry_prompt(
        {"required_resources": ["doctor"]},
        allowed_resources=["doctor", "ct_scanner"],
        active_resource_catalog={
            "doctor": ResourceCatalogEntry(id="doctor", capacity=2, enabled=True),
            "ct_scanner": ResourceCatalogEntry(id="ct_scanner", capacity=1, enabled=True),
        },
        validation_error="missing required field",
        missing_fields=["textual_risk_score", "clinical_category"],
    )

    assert "Use only these active resource ids: doctor, ct_scanner." in prompt
    assert "Active resource catalog" in prompt
    assert "ct_scanner: enabled=True, capacity=1" in prompt
    assert "Validation error: missing required field" in prompt
    assert "Missing or invalid fields: textual_risk_score, clinical_category." in prompt
    assert CLINICAL_ENRICHMENT_JSON_TEMPLATE in prompt
    assert "If you return only required_resources and explanation, the output is invalid." in prompt


def test_extract_active_resource_ids_excludes_disabled_resources() -> None:
    resource_ids = extract_active_resource_ids(
        {
            "doctor": ResourceCatalogEntry(id="doctor", capacity=2, enabled=True),
            "ct_scanner": ResourceCatalogEntry(id="ct_scanner", capacity=0, enabled=True),
            "xray_room": ResourceCatalogEntry(id="xray_room", capacity=0, enabled=False),
        }
    )

    assert resource_ids == ["doctor", "ct_scanner"]


def test_validation_accepts_optional_resource_when_active() -> None:
    extractor = MockClinicalExtractor()
    enrichment = extractor._validate_payload(
        {
            "key_symptoms": ["head trauma"],
            "textual_risk_score": 4,
            "clinical_category": "trauma",
            "deterioration_rate": 0.08,
            "max_wait_time": 10,
            "estimated_service_time": 45,
            "required_resources": ["doctor", "ct_scanner"],
            "explanation": "The head trauma presentation supports imaging and physician review in the simulation.",
        },
        allowed_resources=["doctor", "ct_scanner"],
    )

    assert isinstance(enrichment, ClinicalEnrichment)
    assert enrichment.required_resources == ["doctor", "ct_scanner"]


def test_validation_accepts_enabled_zero_capacity_resource() -> None:
    extractor = MockClinicalExtractor()
    enrichment = extractor._validate_payload(
        {
            "key_symptoms": ["stroke-like symptoms"],
            "textual_risk_score": 4,
            "clinical_category": "neurological",
            "deterioration_rate": 0.08,
            "max_wait_time": 10,
            "estimated_service_time": 45,
            "required_resources": ["doctor", "ct_scanner"],
            "explanation": "The neurological presentation warrants physician review and CT imaging in the simulation.",
        },
        allowed_resources=["doctor", "ct_scanner"],
    )

    assert enrichment.required_resources == ["doctor", "ct_scanner"]


def test_validation_rejects_optional_resource_when_not_active() -> None:
    extractor = MockClinicalExtractor()

    with pytest.raises(LLMExtractionError, match="unsupported resource: ct_scanner"):
        extractor._validate_payload(
            {
                "key_symptoms": ["head trauma"],
                "textual_risk_score": 4,
                "clinical_category": "trauma",
                "deterioration_rate": 0.08,
                "max_wait_time": 10,
                "estimated_service_time": 45,
                "required_resources": ["doctor", "ct_scanner"],
                "explanation": "The head trauma presentation supports imaging and physician review in the simulation.",
            },
            allowed_resources=["doctor"],
        )


def test_validation_rejects_disabled_resource() -> None:
    extractor = MockClinicalExtractor()

    with pytest.raises(LLMExtractionError, match="unsupported resource: ct_scanner"):
        extractor._validate_payload(
            {
                "key_symptoms": ["head trauma"],
                "textual_risk_score": 4,
                "clinical_category": "trauma",
                "deterioration_rate": 0.08,
                "max_wait_time": 10,
                "estimated_service_time": 45,
                "required_resources": ["doctor", "ct_scanner"],
                "explanation": "The head trauma presentation supports imaging and physician review in the simulation.",
            },
            allowed_resources=["doctor"],
        )


def test_ollama_prompt_restricts_resources_to_active_catalog() -> None:
    extractor = OllamaClinicalExtractor(base_url="http://ollama:11434", client=object())
    prompt = extractor._build_prompt(
        build_patient("Head trauma after fall with confusion"),
        allowed_resources=["doctor", "nurse", "ct_scanner"],
        active_resource_catalog={
            "doctor": ResourceCatalogEntry(id="doctor", capacity=2, enabled=True),
            "nurse": ResourceCatalogEntry(id="nurse", capacity=2, enabled=True),
            "ct_scanner": ResourceCatalogEntry(id="ct_scanner", capacity=1, enabled=True),
        },
    )

    assert "Use only the supported resources: doctor, nurse, ct_scanner." in prompt
    assert "Do not invent resource ids." in prompt
    assert "Include optional active resources when they are clinically relevant." in prompt
    assert "Your output must contain exactly this object shape and must not omit any key." in prompt
    assert '"textual_risk_score": 3' in prompt
    assert '"clinical_category": "category"' in prompt
    assert '"estimated_service_time": 45' in prompt
    assert "If you return only required_resources and explanation, the output is invalid." in prompt
