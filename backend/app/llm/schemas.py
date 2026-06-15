from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

DEFAULT_VALID_RESOURCES = (
    "doctor",
    "nurse",
    "observation_bed",
    "resuscitation_room",
    "vital_sign_monitor",
    "laboratory",
    "xray_room",
    "ct_scanner",
    "ultrasound_room",
    "isolation_room",
    "pharmacy",
    "specialist",
)
CLINICAL_ENRICHMENT_SCHEMA_VERSION = "clinical_enrichment_v1"


def build_clinical_enrichment_json_schema(allowed_resources: list[str] | None = None) -> dict:
    valid_resources = list(_resolve_allowed_resources(allowed_resources))
    schema = ClinicalEnrichment.model_json_schema()
    properties = schema.setdefault("properties", {})
    required_resources = properties.setdefault("required_resources", {})
    required_resources["items"] = {"type": "string", "enum": valid_resources}
    return schema


def normalize_enrichment_payload(
    payload: object,
    *,
    allowed_resources: list[str] | None = None,
) -> dict:
    if isinstance(payload, ClinicalEnrichment):
        return payload.model_dump()
    if not isinstance(payload, dict):
        raise TypeError("Clinical enrichment payload must be a dictionary")

    normalized = dict(payload)
    normalized_resources = _normalize_required_resources(
        normalized.get("required_resources"),
        allowed_resources=allowed_resources,
    )
    if "doctor" not in normalized_resources:
        normalized_resources.insert(0, "doctor")
    normalized["required_resources"] = normalized_resources
    return normalized


def _resolve_allowed_resources(allowed_resources: list[str] | None) -> tuple[str, ...]:
    if allowed_resources is None:
        return DEFAULT_VALID_RESOURCES
    normalized = [resource.strip().lower() for resource in allowed_resources if resource.strip()]
    return tuple(dict.fromkeys(normalized)) or DEFAULT_VALID_RESOURCES


def _normalize_required_resources(
    resources: object,
    *,
    allowed_resources: list[str] | None = None,
) -> list[str]:
    if resources is None:
        raise ValueError("required_resources is required")

    if isinstance(resources, str):
        resource_items = [part.strip().lower() for part in resources.split(",") if part.strip()]
    elif isinstance(resources, list):
        resource_items = [str(resource).strip().lower() for resource in resources if str(resource).strip()]
    else:
        raise TypeError("required_resources must be a list or comma-separated string")

    if not resource_items:
        raise ValueError("required_resources must not be empty")

    valid_resources = _resolve_allowed_resources(allowed_resources)
    normalized: list[str] = []
    seen: set[str] = set()
    for resource in resource_items:
        if resource not in valid_resources:
            raise ValueError(f"required_resources contains unsupported resource: {resource}")
        if resource in seen:
            continue
        seen.add(resource)
        normalized.append(resource)
    return normalized


class ClinicalEnrichment(BaseModel):
    key_symptoms: list[str] = Field(default_factory=list)
    textual_risk_score: int = Field(ge=1, le=5)
    clinical_category: str
    deterioration_rate: float = Field(ge=0.0)
    max_wait_time: int = Field(ge=0)
    estimated_service_time: int = Field(ge=1)
    required_resources: list[str] = Field(default_factory=list)
    explanation: str = Field(
        description=(
            "Short non-empty operational justification for the enrichment based only on complaint, "
            "description, acuity, pain, and vital-sign clues. It must justify risk, category, "
            "deterioration, waiting time, service time, and resources, and must not be a diagnosis "
            "or treatment advice."
        )
    )

    @field_validator("key_symptoms", mode="before")
    @classmethod
    def _normalize_symptoms(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("key_symptoms must be a list of strings")
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            symptom = str(item).strip()
            if not symptom:
                continue
            lowered = symptom.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(symptom)
        return normalized

    @field_validator("clinical_category")
    @classmethod
    def _normalize_category(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("clinical_category must not be empty")
        return normalized

    @field_validator("explanation")
    @classmethod
    def _normalize_explanation(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("explanation must not be empty")
        return normalized

    @field_validator("required_resources", mode="before")
    @classmethod
    def _deduplicate_resources(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("required_resources must be a list of strings")
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            resource = str(item).strip()
            if not resource:
                continue
            if resource in seen:
                continue
            seen.add(resource)
            normalized.append(resource)
        return normalized

    @model_validator(mode="after")
    def _validate_required_resources(self) -> "ClinicalEnrichment":
        if "doctor" not in self.required_resources:
            raise ValueError("required_resources must include doctor")
        return self
