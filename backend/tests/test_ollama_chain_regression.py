from __future__ import annotations

import pytest

from app.llm.extractor import ChainedClinicalExtractor, LLMExtractionError, MockClinicalExtractor
from app.llm.ollama_extractor import OllamaClinicalExtractor
from app.llm.provider import get_clinical_extractor
from app.models.patient import Patient


def build_patient() -> Patient:
    return Patient(
        patient_id="P001",
        age=42,
        arrival_time=0,
        chief_complaint="Fever",
        clinical_description="Fever and cough for three days",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=60,
        estimated_service_time=30,
        required_resources=[],
    )


class FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeHTTPClient:
    def __init__(self, payloads: dict | list[dict]) -> None:
        if isinstance(payloads, list):
            self.payloads = list(payloads)
        else:
            self.payloads = [payloads]
        self.calls = 0

    def post(self, *args, **kwargs):
        index = min(self.calls, len(self.payloads) - 1)
        self.calls += 1
        return FakeHTTPResponse(self.payloads[index])


def test_ollama_empty_explanation_retries_and_succeeds() -> None:
    ollama = OllamaClinicalExtractor(
        base_url="http://ollama:11434",
        client=FakeHTTPClient(
            [
                {
                    "response": """
                    {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
                    "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
                    "required_resources":["doctor","nurse","laboratory"],"explanation":""}
                    """
                },
                {
                    "response": """
                    {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
                    "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
                    "required_resources":["doctor","nurse","laboratory"],
                    "explanation":"The respiratory infectious pattern and moderate acuity support elevated priority, shorter waiting tolerance, and laboratory-backed clinical review in the simulator."}
                    """
                },
            ]
        ),
    )
    extractor = ChainedClinicalExtractor(requested_provider="ollama", extractors=[ollama], fallback_to_mock=True)

    enrichment = extractor.enrich_patient(build_patient())
    metadata = extractor.get_metadata()

    assert enrichment.clinical_category == "infectious"
    assert enrichment.explanation
    assert metadata["llm_provider_used"] == "ollama"
    assert metadata["llm_fallback_count"] == 0
    assert metadata["llm_provider_attempts"]["ollama"]["successes"] == 1
    assert metadata["llm_provider_retries"]["ollama"] == 1
    assert metadata["llm_provider_attempts"]["mock"]["successes"] == 0


def test_ollama_empty_explanation_twice_falls_back_to_mock() -> None:
    ollama = OllamaClinicalExtractor(
        base_url="http://ollama:11434",
        client=FakeHTTPClient(
            [
                {
                    "response": """
                    {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
                    "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
                    "required_resources":["doctor","nurse","laboratory"],"explanation":""}
                    """
                },
                {
                    "response": """
                    {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
                    "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
                    "required_resources":["doctor","nurse","laboratory"],"explanation":" "}
                    """
                },
            ]
        ),
    )
    extractor = ChainedClinicalExtractor(requested_provider="ollama", extractors=[ollama], fallback_to_mock=True)

    enrichment = extractor.enrich_patient(build_patient())
    metadata = extractor.get_metadata()

    assert enrichment.clinical_category == "infectious"
    assert metadata["llm_provider_used"] == "mock"
    assert metadata["llm_fallback_count"] == 1
    assert metadata["llm_provider_attempts"]["ollama"]["failures"] == 1
    assert metadata["llm_provider_attempts"]["mock"]["successes"] == 1
    assert metadata["llm_provider_retries"]["ollama"] == 1


def test_ollama_invalid_required_resources_twice_falls_back_to_mock() -> None:
    ollama = OllamaClinicalExtractor(
        base_url="http://ollama:11434",
        client=FakeHTTPClient(
            [
                {
                    "response": """
                    {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
                    "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
                    "required_resources":"unsupported_resource",
                    "explanation":"The infectious presentation indicates moderate operational priority in the simulator."}
                    """
                },
                {
                    "response": """
                    {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
                    "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
                    "required_resources":"unsupported_resource",
                    "explanation":"The infectious presentation indicates moderate operational priority in the simulator."}
                    """
                },
            ]
        ),
    )
    extractor = ChainedClinicalExtractor(requested_provider="ollama", extractors=[ollama], fallback_to_mock=True)

    enrichment = extractor.enrich_patient(build_patient())
    metadata = extractor.get_metadata()

    assert enrichment.clinical_category == "infectious"
    assert metadata["llm_provider_used"] == "mock"
    assert metadata["llm_fallback_count"] == 1
    assert metadata["llm_provider_attempts"]["ollama"]["failures"] == 1
    assert metadata["llm_provider_attempts"]["mock"]["successes"] == 1
    assert metadata["llm_provider_retries"]["ollama"] == 1
    assert metadata["llm_fallback_order"][-1] == "mock"


def test_ollama_incomplete_json_twice_falls_back_to_mock() -> None:
    ollama = OllamaClinicalExtractor(
        base_url="http://ollama:11434",
        client=FakeHTTPClient(
            [
                {
                    "response": """
                    {"required_resources":["doctor","nurse"],"explanation":"Partial output only."}
                    """
                },
                {
                    "response": """
                    {"required_resources":["doctor","nurse"],"explanation":"Partial output only."}
                    """
                },
            ]
        ),
    )
    extractor = ChainedClinicalExtractor(requested_provider="ollama", extractors=[ollama], fallback_to_mock=True)

    enrichment = extractor.enrich_patient(build_patient())
    metadata = extractor.get_metadata()

    assert enrichment.clinical_category == "infectious"
    assert metadata["llm_provider_used"] == "mock"
    assert metadata["llm_fallback_count"] == 1
    assert metadata["llm_provider_attempts"]["ollama"]["failures"] == 1
    assert metadata["llm_provider_attempts"]["mock"]["successes"] == 1


def test_provider_order_defaults_to_ollama_then_mock_even_with_malformed_fallback_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_FALLBACK_ORDER", "broken,unknown")
    monkeypatch.setenv("LLM_FALLBACK_TO_MOCK", "true")

    extractor = get_clinical_extractor()

    assert extractor.get_metadata()["llm_fallback_order"] == ["ollama", "mock"]
    assert extractor.get_metadata()["llm_fallback_order"][-1] != "none"


def test_ollama_validation_error_raises_when_mock_fallback_disabled() -> None:
    ollama = OllamaClinicalExtractor(
        base_url="http://ollama:11434",
        client=FakeHTTPClient(
            [
                {
                    "response": """
                    {"key_symptoms":["fever"],"textual_risk_score":2,"clinical_category":"infectious",
                    "deterioration_rate":0.03,"max_wait_time":60,"estimated_service_time":30,
                    "required_resources":["doctor"],"explanation":""}
                    """
                },
                {
                    "response": """
                    {"key_symptoms":["fever"],"textual_risk_score":2,"clinical_category":"infectious",
                    "deterioration_rate":0.03,"max_wait_time":60,"estimated_service_time":30,
                    "required_resources":["doctor"],"explanation":""}
                    """
                },
            ]
        ),
    )
    extractor = ChainedClinicalExtractor(requested_provider="ollama", extractors=[ollama], fallback_to_mock=False)

    with pytest.raises(LLMExtractionError, match="Structured output validation failed"):
        extractor.enrich_patient(build_patient())
