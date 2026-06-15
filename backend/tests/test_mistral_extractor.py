from __future__ import annotations

import pytest

from app.llm.cache import build_cache_key
from app.llm.extractor import LLMExtractionError
from app.llm.mistral_extractor import MistralClinicalExtractor
from app.models.patient import Patient


def build_patient() -> Patient:
    return Patient(
        patient_id="P001",
        age=51,
        arrival_time=0,
        chief_complaint="Chest pain",
        clinical_description="Chest pain with dyspnea and cold sweat",
        risk_level=3,
        current_risk=3.0,
        deterioration_rate=0.0,
        max_wait_time=30,
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
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls = 0
        self.last_kwargs: dict[str, object] | None = None

    def post(self, *_args: object, **kwargs: object):
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        self.last_kwargs = kwargs
        response = self.responses[index]
        if isinstance(response, Exception):
            raise response
        return FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": response,
                        }
                    }
                ]
            }
        )


def test_mistral_success_returns_valid_clinical_enrichment() -> None:
    client = FakeHTTPClient(
        [
            """
            {"key_symptoms":["chest pain","dyspnea"],"textual_risk_score":4,"clinical_category":"cardiovascular",
            "deterioration_rate":0.09,"max_wait_time":10,"estimated_service_time":60,
            "required_resources":["doctor","nurse","vital_sign_monitor","laboratory"],
            "explanation":"The symptom cluster suggests high operational priority and close monitoring in the simulator."}
            """
        ]
    )
    extractor = MistralClinicalExtractor(api_key="test-key", client=client)

    enrichment = extractor.enrich_patient(build_patient())

    assert enrichment.clinical_category == "cardiovascular"
    assert enrichment.textual_risk_score == 4
    assert "doctor" in enrichment.required_resources


def test_mistral_invalid_explanation_succeeds_on_retry() -> None:
    client = FakeHTTPClient(
        [
            """
            {"key_symptoms":["chest pain","dyspnea"],"textual_risk_score":4,"clinical_category":"cardiovascular",
            "deterioration_rate":0.09,"max_wait_time":10,"estimated_service_time":60,
            "required_resources":["doctor","nurse","vital_sign_monitor","laboratory"],"explanation":""}
            """,
            """
            {"key_symptoms":["chest pain","dyspnea"],"textual_risk_score":4,"clinical_category":"cardiovascular",
            "deterioration_rate":0.09,"max_wait_time":10,"estimated_service_time":60,
            "required_resources":["doctor","nurse","vital_sign_monitor","laboratory"],
            "explanation":"The chest pain and respiratory warning symptoms justify high priority, shorter waiting tolerance, and monitoring resources in the simulation."}
            """,
        ]
    )
    extractor = MistralClinicalExtractor(api_key="test-key", client=client)

    enrichment = extractor.enrich_patient(build_patient())

    assert enrichment.explanation
    assert client.calls == 2
    assert extractor.get_metadata()["llm_provider_retries"]["mistral"] == 1


def test_mistral_invalid_required_resources_succeeds_on_retry() -> None:
    client = FakeHTTPClient(
        [
            """
            {"key_symptoms":["chest pain","dyspnea"],"textual_risk_score":4,"clinical_category":"cardiovascular",
            "deterioration_rate":0.09,"max_wait_time":10,"estimated_service_time":60,
            "required_resources":"bad_resource",
            "explanation":"The chest pain and respiratory warning symptoms justify high priority in the simulator."}
            """,
            """
            {"key_symptoms":["chest pain","dyspnea"],"textual_risk_score":4,"clinical_category":"cardiovascular",
            "deterioration_rate":0.09,"max_wait_time":10,"estimated_service_time":60,
            "required_resources":["doctor","nurse","vital_sign_monitor","laboratory"],
            "explanation":"The warning symptom pattern supports high operational priority and close monitoring resources in the simulation."}
            """,
        ]
    )
    extractor = MistralClinicalExtractor(api_key="test-key", client=client)

    enrichment = extractor.enrich_patient(build_patient())

    assert enrichment.required_resources == ["doctor", "nurse", "vital_sign_monitor", "laboratory"]
    assert extractor.get_metadata()["llm_provider_retries"]["mistral"] == 1


def test_mistral_invalid_structure_raises_when_retry_fails() -> None:
    client = FakeHTTPClient(
        [
            """
            {"key_symptoms":["chest pain"],"textual_risk_score":4,"clinical_category":"cardiovascular",
            "deterioration_rate":0.09,"max_wait_time":10,"estimated_service_time":60,
            "required_resources":"bad_resource","explanation":"Operational note."}
            """,
            """
            {"key_symptoms":["chest pain"],"textual_risk_score":4,"clinical_category":"cardiovascular",
            "deterioration_rate":0.09,"max_wait_time":10,"estimated_service_time":60,
            "required_resources":"bad_resource","explanation":"Operational note."}
            """,
        ]
    )
    extractor = MistralClinicalExtractor(api_key="test-key", client=client)

    with pytest.raises(LLMExtractionError):
        extractor.enrich_patient(build_patient())


def test_cache_key_includes_mistral_provider_and_model() -> None:
    key_a = build_cache_key(
        "Chest pain",
        "Chest pain with dyspnea",
        provider="mistral",
        model="mistral-small-latest",
    )
    key_b = build_cache_key(
        "Chest pain",
        "Chest pain with dyspnea",
        provider="ollama",
        model="llama3.2:3b",
    )

    assert key_a != key_b


def test_mistral_prompt_includes_active_resource_catalog_and_optional_guidance() -> None:
    client = FakeHTTPClient(
        [
            """
            {"key_symptoms":["head trauma","confusion"],"textual_risk_score":4,"clinical_category":"trauma",
            "deterioration_rate":0.09,"max_wait_time":10,"estimated_service_time":60,
            "required_resources":["doctor","ct_scanner"],
            "explanation":"The head trauma presentation supports physician review and imaging in the simulator."}
            """
        ]
    )
    extractor = MistralClinicalExtractor(api_key="test-key", client=client)

    extractor.enrich_patient(
        build_patient(),
        allowed_resources=["doctor", "nurse", "ct_scanner"],
        active_resource_catalog={
            "doctor": {"id": "doctor", "capacity": 2, "enabled": True},
            "nurse": {"id": "nurse", "capacity": 2, "enabled": True},
            "ct_scanner": {"id": "ct_scanner", "capacity": 1, "enabled": True},
        },
    )
    messages = client.last_kwargs["json"]["messages"]  # type: ignore[index]
    combined = "\n".join(message["content"] for message in messages)  # type: ignore[index]

    assert "Available active resources" in combined
    assert "ct_scanner" in combined
    assert "Use only the supported resources: doctor, nurse, ct_scanner." in combined
    assert "Include optional active resources when they are clinically relevant." in combined
