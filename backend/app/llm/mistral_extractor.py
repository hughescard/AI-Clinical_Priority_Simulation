from __future__ import annotations

import json
from typing import Any

import httpx

from app.llm.extractor import LLMExtractionError, SingleProviderClinicalExtractor
from app.llm.prompts import build_structured_output_retry_prompt, build_system_prompt, build_user_prompt
from app.llm.schemas import ClinicalEnrichment
from app.models.patient import Patient


class MistralClinicalExtractor(SingleProviderClinicalExtractor):
    def __init__(
        self,
        api_key: str,
        model: str = "mistral-small-latest",
        *,
        timeout_seconds: float = 30.0,
        cache=None,
        client: Any | None = None,
    ) -> None:
        super().__init__(cache=cache)
        if not api_key.strip():
            raise LLMExtractionError("MISTRAL_API_KEY is required when LLM_PROVIDER=mistral")

        self.provider_name = "mistral"
        self.model_name = model
        self._provider_requested = "mistral"
        self._fallback_order = ["mistral"]
        self._provider_attempts = {"mistral": {"successes": 0, "failures": 0}}
        self._provider_retries = {"mistral": 0}
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self.base_url = "https://api.mistral.ai/v1"
        self.client = client or httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    def _enrich_uncached(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ) -> ClinicalEnrichment:
        raw_response = self._request_payload(
            self._build_messages(
                patient,
                allowed_resources=allowed_resources,
                active_resource_catalog=active_resource_catalog,
            )
        )
        try:
            return self._validate_payload(raw_response, allowed_resources=allowed_resources)
        except LLMExtractionError:
            if not isinstance(raw_response, dict):
                raise

        self._last_retry_attempted = True
        self._provider_retries["mistral"] += 1
        retried_response = self._request_payload(
            [
                {
                    "role": "system",
                    "content": build_system_prompt(
                        allowed_resources,
                        active_resource_catalog=active_resource_catalog,
                    ),
                },
                {
                    "role": "user",
                    "content": build_structured_output_retry_prompt(
                        raw_response,
                        allowed_resources=allowed_resources,
                        active_resource_catalog=active_resource_catalog,
                    ),
                },
            ]
        )
        return self._validate_payload(retried_response, allowed_resources=allowed_resources)

    def _request_payload(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model_name,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 400,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices")
        if not choices or not isinstance(choices, list):
            raise LLMExtractionError("Mistral response did not include choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not content:
            raise LLMExtractionError("Mistral response did not include message content")
        if isinstance(content, list):
            content = "".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(getattr(item, "text", ""))
                for item in content
            ).strip()
        if isinstance(content, dict):
            payload = content
        else:
            try:
                payload = json.loads(str(content))
            except json.JSONDecodeError as exc:
                raise LLMExtractionError(f"Mistral returned invalid JSON content: {exc}") from exc
        if not isinstance(payload, dict):
            raise LLMExtractionError("Mistral response JSON must be an object")
        return payload

    def _build_messages(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": build_system_prompt(
                    allowed_resources,
                    active_resource_catalog=active_resource_catalog,
                ),
            },
            {
                "role": "user",
                "content": (
                    "Return valid JSON only.\n"
                    "Do not return markdown.\n"
                    "Include all required fields.\n"
                    "required_resources must always be an array/list of strings, never a single string.\n"
                    "Explanation must be a non-empty string with one or two sentences.\n"
                    "Explanation must be a short operational justification linked to risk, category, deterioration, waiting time, service time, and resources.\n"
                    f"Use only the supported resources: {', '.join(allowed_resources or [])}.\n"
                    "Always include doctor in required_resources.\n"
                    "Include optional active resources when they are clinically relevant.\n"
                    "Do not provide diagnosis or treatment recommendations.\n"
                    "Do not include markdown, comments, or any text outside the JSON object.\n\n"
                    "Example JSON:\n"
                    "{\n"
                    '  "key_symptoms": ["chest pain", "shortness of breath"],\n'
                    '  "textual_risk_score": 4,\n'
                    '  "clinical_category": "cardiovascular",\n'
                    '  "deterioration_rate": 0.08,\n'
                    '  "max_wait_time": 10,\n'
                    '  "estimated_service_time": 45,\n'
                    '  "required_resources": ["doctor", "nurse", "observation_bed", "vital_sign_monitor"],\n'
                    '  "explanation": "The symptoms and triage fields indicate high operational priority and require close monitoring during simulation planning."\n'
                    "}\n\n"
                    f"{build_user_prompt(patient.chief_complaint, patient.clinical_description, allowed_resources=allowed_resources, active_resource_catalog=active_resource_catalog)}"
                ),
            },
        ]
