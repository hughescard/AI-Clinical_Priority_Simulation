from __future__ import annotations

import pytest

from app.llm.extractor import ChainedClinicalExtractor, ClinicalExtractor, LLMExtractionError, MockClinicalExtractor
from app.llm.provider import get_clinical_extractor
from app.models.patient import Patient


def build_patient(
    chief_complaint: str = "Chest pain",
    clinical_description: str = "Chest pain with dyspnea and cold sweat",
) -> Patient:
    return Patient(
        patient_id="P001",
        age=57,
        arrival_time=0,
        chief_complaint=chief_complaint,
        clinical_description=clinical_description,
        risk_level=3,
        current_risk=3.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=30,
        required_resources=[],
    )


class FakeExtractor(ClinicalExtractor):
    def __init__(self, provider_name: str, model_name: str, *, result=None, error: Exception | None = None) -> None:
        super().__init__()
        self.provider_name = provider_name
        self.model_name = model_name
        self.result = result
        self.error = error

    def enrich_patient(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ):
        if self.error is not None:
            raise self.error
        return self.result


def test_llm_provider_mock_uses_mock_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    extractor = get_clinical_extractor()

    assert isinstance(extractor, MockClinicalExtractor)


def test_mistral_failure_falls_back_to_ollama() -> None:
    mock_result = MockClinicalExtractor().enrich_patient(build_patient("Fever", "Fever and cough for three days"))
    mistral = FakeExtractor("mistral", "mistral-small-latest", error=LLMExtractionError("rate limit"))
    ollama = FakeExtractor("ollama", "llama3.2:3b", result=mock_result)
    extractor = ChainedClinicalExtractor(requested_provider="mistral", extractors=[mistral, ollama])

    enrichment = extractor.enrich_patient(build_patient("Fever", "Fever and cough for three days"))
    metadata = extractor.get_metadata()

    assert enrichment == mock_result
    assert metadata["llm_provider_used"] == "ollama"
    assert metadata["llm_fallback_count"] == 1
    assert metadata["llm_fallback_order"] == ["mistral", "ollama", "mock"]
    assert metadata["llm_provider_attempts"]["mistral"]["failures"] == 1
    assert metadata["llm_provider_attempts"]["ollama"]["successes"] == 1


def test_ollama_failure_falls_back_to_mock() -> None:
    mock_extractor = MockClinicalExtractor()
    mock_result = mock_extractor.enrich_patient(build_patient("Fever", "Fever and cough for three days"))
    ollama = FakeExtractor("ollama", "llama3.2:3b", error=RuntimeError("connection refused"))
    mock = FakeExtractor("mock", "mock", result=mock_result)
    extractor = ChainedClinicalExtractor(requested_provider="ollama", extractors=[ollama, mock])

    enrichment = extractor.enrich_patient(build_patient("Fever", "Fever and cough for three days"))

    assert enrichment == mock_result
    assert extractor.get_metadata()["llm_provider_used"] == "mock"


def test_mistral_and_ollama_fail_fall_back_to_mock() -> None:
    mock_result = MockClinicalExtractor().enrich_patient(build_patient("Fever", "Fever and cough for three days"))
    extractor = ChainedClinicalExtractor(
        requested_provider="mistral",
        extractors=[
            FakeExtractor("mistral", "mistral-small-latest", error=RuntimeError("403")),
            FakeExtractor("ollama", "llama3.2:3b", error=RuntimeError("connection refused")),
            FakeExtractor("mock", "mock", result=mock_result),
        ],
    )

    enrichment = extractor.enrich_patient(build_patient("Fever", "Fever and cough for three days"))
    metadata = extractor.get_metadata()

    assert enrichment == mock_result
    assert metadata["llm_provider_used"] == "mock"
    assert metadata["llm_provider_attempts"]["mistral"]["failures"] == 1
    assert metadata["llm_provider_attempts"]["ollama"]["failures"] == 1
    assert metadata["llm_provider_attempts"]["mock"]["successes"] == 1


def test_fallback_disabled_raises_last_provider_error() -> None:
    extractor = ChainedClinicalExtractor(
        requested_provider="ollama",
        extractors=[FakeExtractor("ollama", "llama3.2:3b", error=RuntimeError("down"))],
        fallback_to_mock=False,
    )

    with pytest.raises(RuntimeError, match="down"):
        extractor.enrich_patient(build_patient())


def test_provider_attempt_metrics_increment_correctly() -> None:
    result = MockClinicalExtractor().enrich_patient(build_patient())
    extractor = ChainedClinicalExtractor(
        requested_provider="mistral",
        extractors=[
            FakeExtractor("mistral", "mistral-small-latest", error=RuntimeError("quota")),
            FakeExtractor("mock", "mock", result=result),
        ],
    )

    extractor.enrich_patient(build_patient())
    attempts = extractor.get_metadata()["llm_provider_attempts"]

    assert attempts["mistral"] == {"successes": 0, "failures": 1}
    assert attempts["mock"] == {"successes": 1, "failures": 0}


def test_chain_appends_mock_when_fallback_enabled() -> None:
    extractor = ChainedClinicalExtractor(
        requested_provider="ollama",
        extractors=[FakeExtractor("ollama", "llama3.2:3b", error=RuntimeError("bad payload"))],
        fallback_to_mock=True,
    )

    enrichment = extractor.enrich_patient(build_patient("Fever", "Fever and cough for three days"))

    assert enrichment.clinical_category == "infectious"
    assert extractor.get_metadata()["llm_provider_used"] == "mock"


def test_validate_payload_wraps_normalization_type_error() -> None:
    extractor = MockClinicalExtractor()

    with pytest.raises(LLMExtractionError, match="Structured output validation failed: required_resources must be a list or comma-separated string"):
        extractor._validate_payload(
            {
                "key_symptoms": ["fever"],
                "textual_risk_score": 2,
                "clinical_category": "infectious",
                "deterioration_rate": 0.03,
                "max_wait_time": 60,
                "estimated_service_time": 30,
                "required_resources": 123,
                "explanation": "Operational explanation.",
            }
        )
