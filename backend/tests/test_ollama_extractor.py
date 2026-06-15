from __future__ import annotations

from app.llm.ollama_extractor import OllamaClinicalExtractor
from app.models.patient import Patient


def build_patient() -> Patient:
    return Patient(
        patient_id="P001",
        age=28,
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
        self.requests: list[dict] = []

    def post(self, *args, **kwargs):
        self.calls += 1
        self.requests.append(kwargs)
        index = min(self.calls - 1, len(self.payloads) - 1)
        return FakeHTTPResponse(self.payloads[index])


def test_ollama_success_returns_clinical_enrichment() -> None:
    client = FakeHTTPClient(
        {
            "response": """
            {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
            "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
            "required_resources":["doctor","nurse","laboratory"],"explanation":"Infectious respiratory syndrome."}
            """
        }
    )
    extractor = OllamaClinicalExtractor(base_url="http://ollama:11434", client=client)

    enrichment = extractor.enrich_patient(build_patient())

    assert enrichment.clinical_category == "infectious"
    assert "laboratory" in enrichment.required_resources


def test_ollama_normalizes_comma_separated_required_resources() -> None:
    client = FakeHTTPClient(
        {
            "response": """
            {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
            "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
            "required_resources":"doctor,nurse","explanation":"The infectious symptom cluster warrants doctor and nurse review with moderate waiting tolerance in the simulator."}
            """
        }
    )
    extractor = OllamaClinicalExtractor(base_url="http://ollama:11434", client=client)

    enrichment = extractor.enrich_patient(build_patient())

    assert enrichment.required_resources == ["doctor", "nurse"]


def test_ollama_normalizes_single_required_resource_string() -> None:
    client = FakeHTTPClient(
        {
            "response": """
            {"key_symptoms":["fever"],"textual_risk_score":2,"clinical_category":"infectious",
            "deterioration_rate":0.03,"max_wait_time":60,"estimated_service_time":30,
            "required_resources":"doctor","explanation":"The low-complexity infectious presentation still requires physician review in the simulation."}
            """
        }
    )
    extractor = OllamaClinicalExtractor(base_url="http://ollama:11434", client=client)

    enrichment = extractor.enrich_patient(build_patient())

    assert enrichment.required_resources == ["doctor"]


def test_ollama_retries_once_for_empty_explanation() -> None:
    client = FakeHTTPClient(
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
                "explanation":"The triage text suggests moderate infectious risk with limited waiting tolerance and a need for doctor, nurse, and laboratory support in the simulation."}
                """
            },
        ]
    )
    extractor = OllamaClinicalExtractor(base_url="http://ollama:11434", client=client)

    enrichment = extractor.enrich_patient(build_patient())

    assert enrichment.explanation
    assert client.calls == 2
    assert extractor.get_metadata()["llm_provider_retries"]["ollama"] == 1


def test_ollama_retries_once_for_invalid_required_resources() -> None:
    client = FakeHTTPClient(
        [
            {
                "response": """
                {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
                "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
                "required_resources":"bad_resource","explanation":"The infectious presentation suggests moderate priority in simulation triage."}
                """
            },
            {
                "response": """
                {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
                "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
                "required_resources":["doctor","nurse","laboratory"],
                "explanation":"The infectious presentation supports elevated review priority, shorter waiting tolerance, and laboratory support in the simulator."}
                """
            },
        ]
    )
    extractor = OllamaClinicalExtractor(base_url="http://ollama:11434", client=client)

    enrichment = extractor.enrich_patient(build_patient())

    assert enrichment.required_resources == ["doctor", "nurse", "laboratory"]
    assert client.calls == 2
    assert extractor.get_metadata()["llm_provider_retries"]["ollama"] == 1


def test_ollama_retries_once_for_incomplete_json() -> None:
    client = FakeHTTPClient(
        [
            {
                "response": """
                {"required_resources":["doctor","nurse"],"explanation":"Partial output only."}
                """
            },
            {
                "response": """
                {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
                "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
                "required_resources":["doctor","nurse","laboratory"],
                "explanation":"The infectious respiratory pattern suggests moderate urgency, shorter waiting tolerance, and laboratory-backed clinician review in the simulator."}
                """
            },
        ]
    )
    extractor = OllamaClinicalExtractor(base_url="http://ollama:11434", client=client)

    enrichment = extractor.enrich_patient(build_patient())

    assert enrichment.clinical_category == "infectious"
    assert client.calls == 2
    retry_prompt = client.requests[1]["json"]["prompt"]
    assert "Missing or invalid fields: key_symptoms, textual_risk_score, clinical_category, deterioration_rate, max_wait_time, estimated_service_time." in retry_prompt


def test_ollama_request_uses_deterministic_generation_options() -> None:
    client = FakeHTTPClient(
        {
            "response": """
            {"key_symptoms":["fever","cough"],"textual_risk_score":3,"clinical_category":"infectious",
            "deterioration_rate":0.05,"max_wait_time":30,"estimated_service_time":45,
            "required_resources":["doctor","nurse","laboratory"],"explanation":"Infectious respiratory syndrome."}
            """
        }
    )
    extractor = OllamaClinicalExtractor(base_url="http://ollama:11434", client=client)

    extractor.enrich_patient(build_patient())

    request_payload = client.requests[0]["json"]
    assert request_payload["format"] == "json"
    assert request_payload["options"]["temperature"] == 0
    assert request_payload["options"]["top_p"] == 0.1
    assert request_payload["options"]["num_predict"] == 700
