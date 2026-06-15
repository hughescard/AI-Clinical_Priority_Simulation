from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.patient import Patient

RESOURCE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class ResourceCatalogEntry(BaseModel):
    id: str
    capacity: int = Field(ge=0)
    enabled: bool = True

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not RESOURCE_ID_PATTERN.fullmatch(normalized):
            raise ValueError("resource id must be lowercase snake_case")
        return normalized


class AdvancedScenarioConfig(BaseModel):
    resources: list[ResourceCatalogEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ensure_unique_ids(self) -> "AdvancedScenarioConfig":
        seen: set[str] = set()
        duplicates: set[str] = set()
        for resource in self.resources:
            if resource.id in seen:
                duplicates.add(resource.id)
            seen.add(resource.id)
        if duplicates:
            duplicate_list = ", ".join(sorted(duplicates))
            raise ValueError(f"duplicate resource ids are not allowed: {duplicate_list}")
        return self

    def to_capacity_map(self) -> dict[str, int]:
        return {resource.id: resource.capacity for resource in self.resources if resource.enabled}

    def to_catalog_map(self) -> dict[str, dict[str, int | bool | str]]:
        return {
            resource.id: {
                "id": resource.id,
                "capacity": resource.capacity,
                "enabled": resource.enabled,
            }
            for resource in self.resources
        }


def build_active_resource_catalog(
    base_capacities: dict[str, int],
    advanced_config: AdvancedScenarioConfig | None = None,
) -> tuple[dict[str, int], dict[str, ResourceCatalogEntry]]:
    capacities = {resource_id: max(0, int(capacity)) for resource_id, capacity in base_capacities.items()}
    if advanced_config is None:
        catalog = {
            resource_id: ResourceCatalogEntry(id=resource_id, capacity=capacity, enabled=True)
            for resource_id, capacity in capacities.items()
        }
        return capacities, catalog

    for resource in advanced_config.resources:
        capacities[resource.id] = resource.capacity if resource.enabled else 0

    catalog = {
        resource_id: ResourceCatalogEntry(
            id=resource_id,
            capacity=capacity,
            enabled=capacity > 0 or (
                any(config_resource.id == resource_id and config_resource.enabled for config_resource in advanced_config.resources)
                if advanced_config is not None
                else True
            ),
        )
        for resource_id, capacity in capacities.items()
    }
    if advanced_config is not None:
        for resource in advanced_config.resources:
            catalog[resource.id] = ResourceCatalogEntry(
                id=resource.id,
                capacity=capacities.get(resource.id, 0),
                enabled=resource.enabled,
            )
    return capacities, catalog


class SimulationConfig(BaseModel):
    algorithm: str
    scenario: str
    seed: int
    data_source: str = "synthetic"
    duration_minutes: int = Field(gt=0)
    doctor_round_interval_minutes: int = Field(gt=0)
    deterioration_interval_minutes: int = Field(gt=0)
    resource_capacities: dict[str, int]
    active_resource_catalog: dict[str, ResourceCatalogEntry] = Field(default_factory=dict)
    advanced_config: AdvancedScenarioConfig | None = None


class SimulationState(BaseModel):
    current_time: float = 0
    waiting_patients: list[Patient] = Field(default_factory=list)
    active_patients: list[Patient] = Field(default_factory=list)
    completed_patients: list[Patient] = Field(default_factory=list)
    timeline: list[dict] = Field(default_factory=list)


class WaitingReasonEvent(BaseModel):
    time: float
    trigger: str | None = None
    blocking_resources: list[str] = Field(default_factory=list)
    available_resources: dict[str, int] = Field(default_factory=dict)
    message: str | None = None


class PatientTrace(BaseModel):
    patient_id: str
    arrival_time: float
    initial_assessment_time: float | None = None
    time_to_initial_assessment: float | None = None
    service_start_time: float | None = None
    service_end_time: float | None = None
    waiting_time: float | None = None
    service_time: float | None = None
    final_status: str
    clinical_category: str | None = None
    risk_level: int | None = None
    current_risk: float | None = None
    textual_risk_score: int | None = None
    deterioration_rate: float | None = None
    max_wait_time: int | None = None
    estimated_service_time: int | None = None
    required_resources: list[str] = Field(default_factory=list)
    allocated_resources: list[str] = Field(default_factory=list)
    resources_released: list[str] = Field(default_factory=list)
    service_start_trigger: str | None = None
    algorithm: str
    deterioration_events_count: int = 0
    deterioration_times: list[float] = Field(default_factory=list)
    deteriorated_while_waiting: bool = False
    critical_waiting: bool = False
    immediate_service: bool = False
    llm_provider_used: str | None = None
    llm_explanation: str | None = None
    waiting_reason_events: list[WaitingReasonEvent] = Field(default_factory=list)
    timeline_event_ids: list[int] = Field(default_factory=list)


class SimulationResult(BaseModel):
    algorithm: str
    scenario: str
    seed: int
    duration_minutes: int
    data_source: str
    dataset_records_used: int | None = None
    dataset_name: str | None = None
    metrics: dict
    resource_summary: dict = Field(default_factory=dict)
    active_resource_catalog: dict[str, dict] = Field(default_factory=dict)
    advanced_config: dict | None = None
    patient_status_summary: dict = Field(default_factory=dict)
    event_counts: dict = Field(default_factory=dict)
    llm_provider_requested: str | None = None
    llm_provider_used: str | None = None
    llm_fallback_order: list[str] = Field(default_factory=list)
    llm_fallback_count: int = 0
    llm_cache_hits: int = 0
    llm_cache_misses: int = 0
    llm_provider_attempts: dict[str, dict[str, int]] = Field(default_factory=dict)
    llm_provider_retries: dict[str, int] = Field(default_factory=dict)
    patient_traces: list[PatientTrace] = Field(default_factory=list)
    timeline: list[dict]
