from __future__ import annotations

import json
from typing import Any

import httpx

from app.llm.extractor import LLMExtractionError, SingleProviderClinicalExtractor
from app.llm.prompts import (
    CLINICAL_ENRICHMENT_JSON_TEMPLATE,
    build_structured_output_retry_prompt,
    build_system_prompt,
    build_user_prompt,
)
from app.llm.schemas import ClinicalEnrichment
from app.models.patient import Patient


class OllamaClinicalExtractor(SingleProviderClinicalExtractor):
    def __init__(
        self,
        base_url: str,
        model: str = "llama3.2:3b",
        *,
        timeout_seconds: float = 30.0,
        cache=None,
        client: Any | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self.provider_name = "ollama"
        self.model_name = model
        self._provider_requested = "ollama"
        self._fallback_order = ["ollama"]
        self._provider_attempts = {"ollama": {"successes": 0, "failures": 0}}
        self._provider_retries = {"ollama": 0}
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(timeout=self.timeout_seconds)

    def _enrich_uncached(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ) -> ClinicalEnrichment:
        raw_response = self._request_payload(
            self._build_prompt(
                patient,
                allowed_resources=allowed_resources,
                active_resource_catalog=active_resource_catalog,
            )
        )
        try:
            return self._validate_payload(raw_response, allowed_resources=allowed_resources)
        except LLMExtractionError as exc:
            if not isinstance(raw_response, dict):
                raise
            validation_error = str(exc)

        self._last_retry_attempted = True
        self._provider_retries["ollama"] += 1
        missing_fields = self._detect_missing_fields(raw_response)
        retried_response = self._request_payload(
            build_structured_output_retry_prompt(
                raw_response,
                allowed_resources=allowed_resources,
                active_resource_catalog=active_resource_catalog,
                validation_error=validation_error,
                missing_fields=missing_fields,
            )
        )
        return self._validate_payload(retried_response, allowed_resources=allowed_resources)

    def _request_payload(self, prompt: str) -> dict[str, Any]:
        response = self.client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "stream": False,
                "format": "json",
                "prompt": prompt,
                "options": {
                    "temperature": 0,
                    "top_p": 0.1,
                    "num_predict": 700,
                },
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        raw_response = payload.get("response")
        if isinstance(raw_response, str):
            try:
                raw_response = json.loads(raw_response)
            except json.JSONDecodeError as exc:
                raise LLMExtractionError(f"Ollama returned invalid JSON content: {exc}") from exc
        if not isinstance(raw_response, dict):
            raise LLMExtractionError("Ollama response did not contain a JSON object")
        return raw_response

    def _build_prompt(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ) -> str:
        return (
            f"{build_system_prompt(allowed_resources, active_resource_catalog=active_resource_catalog)}\n\n"
            "Return valid JSON only.\n"
            "Do not return markdown.\n"
            "Include all required fields.\n"
            "Your output must contain exactly this object shape and must not omit any key.\n"
            "Use numeric values for textual_risk_score, deterioration_rate, max_wait_time, and estimated_service_time.\n"
            "required_resources must always be an array/list of strings, never a single string.\n"
            "Explanation must be a non-empty string with one or two sentences.\n"
            "Explanation must be a short operational justification linked to risk, category, deterioration, waiting time, service time, and resources.\n"
            f"Use only the supported resources: {', '.join(allowed_resources or [])}.\n"
            "Always include doctor in required_resources.\n"
            "Include optional active resources when they are clinically relevant.\n"
            "If you return only required_resources and explanation, the output is invalid.\n"
            "Do not provide diagnosis or treatment recommendations.\n"
            "Do not include markdown, comments, or any text outside the JSON object.\n\n"
            "Required JSON template:\n"
            f"{CLINICAL_ENRICHMENT_JSON_TEMPLATE}\n\n"
            f"{build_user_prompt(patient.chief_complaint, patient.clinical_description, allowed_resources=allowed_resources, active_resource_catalog=active_resource_catalog)}"
        )

    def _detect_missing_fields(self, payload: dict[str, Any]) -> list[str]:
        required_fields = [
            "key_symptoms",
            "textual_risk_score",
            "clinical_category",
            "deterioration_rate",
            "max_wait_time",
            "estimated_service_time",
            "required_resources",
            "explanation",
        ]
        missing_fields: list[str] = []
        for field_name in required_fields:
            if field_name not in payload:
                missing_fields.append(field_name)
                continue
            value = payload.get(field_name)
            if isinstance(value, str) and not value.strip():
                missing_fields.append(field_name)
        return missing_fields
