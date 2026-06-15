from __future__ import annotations

import random

from app.config import settings
from app.data.dataset_registry import get_data_source_label, get_dataset_records
from app.data.normalization import convert_record_to_patient
from app.llm.extractor import ClinicalExtractor
from app.llm.prompts import extract_active_resource_ids
from app.llm.provider import get_clinical_extractor
from app.models.patient import Patient
from app.models.simulation import AdvancedScenarioConfig, ResourceCatalogEntry, build_active_resource_catalog


class ScenarioGenerator:
    _complaints = [
        ("Chest pain", "Possible acute coronary syndrome", ["doctor", "nurse", "vital_sign_monitor", "laboratory"]),
        ("Dyspnea", "Respiratory distress with tachypnea", ["doctor", "nurse", "observation_bed", "vital_sign_monitor"]),
        ("Fever", "Infectious syndrome under evaluation", ["doctor", "nurse", "laboratory"]),
        ("Trauma", "Blunt trauma requiring observation", ["doctor", "nurse", "observation_bed"]),
        ("Cardiac arrest", "Critical collapse requiring full response", ["doctor", "nurse", "resuscitation_room", "vital_sign_monitor"]),
    ]

    _scenario_profiles = {
        "normal": {"patient_count": 18, "interarrival_min": 8, "interarrival_max": 30, "resource_modifier": {}},
        "high_demand": {"patient_count": 28, "interarrival_min": 4, "interarrival_max": 16, "resource_modifier": {}},
        "limited_resources": {
            "patient_count": 18,
            "interarrival_min": 8,
            "interarrival_max": 22,
            "resource_modifier": {"doctor": -1, "nurse": -1, "observation_bed": -2, "laboratory": -1},
        },
    }

    def __init__(
        self,
        seed: int,
        extractor: ClinicalExtractor | None = None,
        data_source: str = "synthetic",
        *,
        base_resource_capacities: dict[str, int] | None = None,
        advanced_config: AdvancedScenarioConfig | None = None,
    ) -> None:
        self._random = random.Random(seed)
        self._extractor = extractor or get_clinical_extractor()
        self._seed = seed
        self._data_source = data_source
        self._base_resource_capacities = dict(base_resource_capacities or settings.default_resource_capacity.copy())
        self._advanced_config = advanced_config
        _, self._active_resource_catalog = build_active_resource_catalog(
            self._base_resource_capacities,
            advanced_config,
        )
        self._scenario_metadata: dict[str, object] = {
            "data_source": data_source,
            "dataset_records_used": None,
            "dataset_name": get_data_source_label(data_source),
        }

    @property
    def extractor_metadata(self) -> dict[str, object]:
        return self._extractor.get_metadata()

    @property
    def scenario_metadata(self) -> dict[str, object]:
        return dict(self._scenario_metadata)

    @property
    def active_resource_catalog(self) -> dict[str, ResourceCatalogEntry]:
        return dict(self._active_resource_catalog)

    def generate(self, scenario: str, duration_minutes: int) -> tuple[list[Patient], dict[str, int]]:
        if scenario not in self._scenario_profiles:
            raise ValueError(f"Unsupported scenario: {scenario}")
        profile = self._scenario_profiles[scenario]
        capacities = self._base_resource_capacities.copy()
        for resource, delta in profile["resource_modifier"].items():
            capacities[resource] = max(0, capacities[resource] + delta)
        capacities, self._active_resource_catalog = build_active_resource_catalog(capacities, self._advanced_config)
        if self._data_source != "synthetic":
            return self._generate_from_dataset(profile, duration_minutes, capacities)
        active_resource_ids = extract_active_resource_ids(self._active_resource_catalog)
        patients: list[Patient] = []
        current_arrival = 0
        for index in range(profile["patient_count"]):
            current_arrival += self._random.randint(profile["interarrival_min"], profile["interarrival_max"])
            if current_arrival >= duration_minutes:
                break
            chief_complaint, clinical_description, _resources = self._random.choice(self._complaints)
            risk_level = self._sample_risk_level(chief_complaint)
            patient = Patient(
                patient_id=f"P{index + 1:03d}",
                age=self._random.randint(1, 95),
                arrival_time=current_arrival,
                chief_complaint=chief_complaint,
                clinical_description=clinical_description,
                risk_level=risk_level,
                current_risk=float(risk_level),
                deterioration_rate=0.0,
                max_wait_time=self._max_wait_for_risk(risk_level),
                estimated_service_time=30,
                required_resources=[],
            )
            enrichment = self._extractor.enrich_patient(
                patient,
                allowed_resources=active_resource_ids,
                active_resource_catalog=self._active_resource_catalog,
            )
            patient.key_symptoms = list(enrichment.key_symptoms)
            patient.textual_risk_score = enrichment.textual_risk_score
            patient.clinical_category = enrichment.clinical_category
            patient.enrichment_explanation = enrichment.explanation
            patient.current_risk = round((patient.risk_level + enrichment.textual_risk_score) / 2, 2)
            patient.deterioration_rate = enrichment.deterioration_rate
            patient.max_wait_time = enrichment.max_wait_time
            patient.estimated_service_time = enrichment.estimated_service_time
            patient.required_resources = list(enrichment.required_resources)
            patients.append(patient)
        self._scenario_metadata = {
            "data_source": self._data_source,
            "dataset_records_used": None,
            "dataset_name": get_data_source_label(self._data_source),
        }
        return patients, capacities

    def _generate_from_dataset(
        self,
        profile: dict,
        duration_minutes: int,
        capacities: dict[str, int],
    ) -> tuple[list[Patient], dict[str, int]]:
        records = get_dataset_records(self._data_source)
        ordered_records = sorted(records, key=lambda record: (record.external_id, record.chief_complaint))
        shuffled_records = list(ordered_records)
        self._random.shuffle(shuffled_records)
        limit = min(profile["patient_count"], len(shuffled_records))
        selected_records = shuffled_records[:limit]
        self._scenario_metadata = {
            "data_source": self._data_source,
            "dataset_records_used": len(selected_records),
            "dataset_name": get_data_source_label(self._data_source),
        }
        patients: list[Patient] = []
        active_resource_ids = extract_active_resource_ids(self._active_resource_catalog)
        current_arrival = 0
        for index, record in enumerate(selected_records):
            if record.arrival_time is None:
                current_arrival += self._random.randint(profile["interarrival_min"], profile["interarrival_max"])
            else:
                current_arrival = record.arrival_time if index == 0 else max(current_arrival, record.arrival_time)
            if current_arrival >= duration_minutes:
                break
            patient = convert_record_to_patient(
                record,
                seed=self._seed,
                index=index,
                fallback_arrival_time=current_arrival,
            )
            patient.arrival_time = float(current_arrival)
            enrichment = self._extractor.enrich_patient(
                patient,
                allowed_resources=active_resource_ids,
                active_resource_catalog=self._active_resource_catalog,
            )
            patient.key_symptoms = list(enrichment.key_symptoms)
            patient.textual_risk_score = enrichment.textual_risk_score
            patient.clinical_category = enrichment.clinical_category
            patient.enrichment_explanation = enrichment.explanation
            patient.current_risk = round((patient.risk_level + enrichment.textual_risk_score) / 2, 2)
            patient.deterioration_rate = enrichment.deterioration_rate
            patient.max_wait_time = enrichment.max_wait_time
            patient.estimated_service_time = enrichment.estimated_service_time
            patient.required_resources = list(enrichment.required_resources)
            patients.append(patient)
        return patients, capacities

    def _sample_risk_level(self, complaint: str) -> int:
        if complaint == "Cardiac arrest":
            return 5
        if complaint == "Chest pain":
            return self._random.choice([3, 4, 4, 5])
        if complaint == "Dyspnea":
            return self._random.choice([2, 3, 4])
        if complaint == "Trauma":
            return self._random.choice([2, 3, 4])
        return self._random.choice([1, 2, 2, 3])

    def _max_wait_for_risk(self, risk_level: int) -> int:
        return {5: 0, 4: 10, 3: 30, 2: 60, 1: 120}[risk_level]
