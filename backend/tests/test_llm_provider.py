from __future__ import annotations

import pytest

from app.llm.extractor import ChainedClinicalExtractor, ClinicalExtractor, MockClinicalExtractor
from app.llm.provider import get_clinical_extractor
from app.models.patient import Patient


def build_patient() -> Patient:
    return Patient(
        patient_id="P001",
        age=45,
        arrival_time=0,
        chief_complaint="Chest pain",
        clinical_description="Chest pain with dyspnea",
        risk_level=3,
        current_risk=3.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=30,
        required_resources=[],
    )


class FailingExtractor(ClinicalExtractor):
    def __init__(self, provider_name: str, model_name: str, error: Exception) -> None:
        super().__init__()
        self.provider_name = provider_name
        self.model_name = model_name
        self.error = error

    def enrich_patient(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ):
        raise self.error


def test_default_provider_is_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    extractor = get_clinical_extractor()

    assert isinstance(extractor, MockClinicalExtractor)
    assert extractor.provider_name == "mock"


def test_provider_can_select_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    extractor = get_clinical_extractor()

    assert isinstance(extractor, MockClinicalExtractor)


def test_provider_can_select_mistral_with_default_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    monkeypatch.setenv("MISTRAL_MODEL", "mistral-small-latest")
    monkeypatch.setenv("LLM_FALLBACK_ORDER", "ollama,mock")
    monkeypatch.setenv("LLM_FALLBACK_TO_MOCK", "true")

    extractor = get_clinical_extractor()

    assert isinstance(extractor, ChainedClinicalExtractor)
    assert extractor.get_metadata()["llm_provider_requested"] == "mistral"
    assert extractor.get_metadata()["llm_fallback_order"] == ["mistral", "ollama", "mock"]


def test_provider_can_select_openai_with_fallback_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("LLM_FALLBACK_ORDER", "ollama,mock")
    monkeypatch.setenv("LLM_FALLBACK_TO_MOCK", "true")

    extractor = get_clinical_extractor()

    assert isinstance(extractor, ChainedClinicalExtractor)
    assert extractor.get_metadata()["llm_provider_requested"] == "openai"
    assert extractor.get_metadata()["llm_fallback_order"] == ["openai", "ollama", "mock"]


def test_mistral_without_mock_fallback_raises_when_all_non_mock_providers_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.setenv("LLM_FALLBACK_TO_MOCK", "false")

    extractor = get_clinical_extractor(
        provider_overrides={
            "ollama": FailingExtractor("ollama", "llama3.2:3b", RuntimeError("ollama down")),
        }
    )

    with pytest.raises(RuntimeError, match="ollama down"):
        extractor.enrich_patient(build_patient())
