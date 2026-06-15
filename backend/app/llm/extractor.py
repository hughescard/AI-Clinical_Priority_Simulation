from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import ValidationError

from app.config import settings
from app.llm.cache import ClinicalEnrichmentCache
from app.llm.prompts import extract_active_resource_ids
from app.llm.schemas import (
    CLINICAL_ENRICHMENT_SCHEMA_VERSION,
    ClinicalEnrichment,
    normalize_enrichment_payload,
)
from app.models.patient import Patient

logger = logging.getLogger(__name__)


class LLMExtractionError(RuntimeError):
    pass


class ClinicalExtractor(ABC):
    provider_name: str
    model_name: str
    schema_version: str

    def __init__(self) -> None:
        self.provider_name = "unknown"
        self.model_name = "unknown"
        self.schema_version = CLINICAL_ENRICHMENT_SCHEMA_VERSION
        self._cache_hits = 0
        self._cache_misses = 0
        self._fallback_count = 0
        self._provider_requested = self.provider_name
        self._fallback_order: list[str] = [self.provider_name]
        self._provider_attempts: dict[str, dict[str, int]] = {}
        self._provider_retries: dict[str, int] = {}
        self._last_retry_attempted = False

    @abstractmethod
    def enrich_patient(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, Any] | None = None,
    ) -> ClinicalEnrichment:
        raise NotImplementedError

    @property
    def cache_hits(self) -> int:
        return self._cache_hits

    @property
    def cache_misses(self) -> int:
        return self._cache_misses

    @property
    def fallback_count(self) -> int:
        return self._fallback_count

    def get_metadata(self) -> dict[str, Any]:
        return {
            "llm_provider_requested": self._provider_requested,
            "llm_provider_used": self.provider_name,
            "llm_fallback_order": list(self._fallback_order),
            "llm_fallback_count": self.fallback_count,
            "llm_cache_hits": self.cache_hits,
            "llm_cache_misses": self.cache_misses,
            "llm_provider_attempts": self._provider_attempts,
            "llm_provider_retries": self._provider_retries,
        }

    def _read_cache(
        self,
        cache: ClinicalEnrichmentCache | None,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, Any] | None = None,
    ) -> ClinicalEnrichment | None:
        if cache is None:
            return None
        cached = cache.get(
            patient.chief_complaint,
            patient.clinical_description,
            provider=self.provider_name,
            model=self.model_name,
            schema_version=self.schema_version,
            allowed_resources=allowed_resources,
            active_resource_catalog=active_resource_catalog,
        )
        if cached is None:
            self._cache_misses += 1
            return None
        self._cache_hits += 1
        return cached

    def _write_cache(
        self,
        cache: ClinicalEnrichmentCache | None,
        patient: Patient,
        enrichment: ClinicalEnrichment,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, Any] | None = None,
    ) -> None:
        if cache is None:
            return
        cache.set(
            patient.chief_complaint,
            patient.clinical_description,
            enrichment,
            provider=self.provider_name,
            model=self.model_name,
            schema_version=self.schema_version,
            allowed_resources=allowed_resources,
            active_resource_catalog=active_resource_catalog,
        )

    def _validate_payload(
        self,
        payload: Any,
        *,
        allowed_resources: list[str] | None = None,
    ) -> ClinicalEnrichment:
        try:
            return ClinicalEnrichment.model_validate(
                normalize_enrichment_payload(payload, allowed_resources=allowed_resources)
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise LLMExtractionError(f"Structured output validation failed: {exc}") from exc


class SingleProviderClinicalExtractor(ClinicalExtractor, ABC):
    def __init__(self, cache: ClinicalEnrichmentCache | None = None) -> None:
        super().__init__()
        self.cache = cache

    def enrich_patient(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, Any] | None = None,
    ) -> ClinicalEnrichment:
        self._last_retry_attempted = False
        cached = self._read_cache(
            self.cache,
            patient,
            allowed_resources=allowed_resources,
            active_resource_catalog=active_resource_catalog,
        )
        if cached is not None:
            return cached
        if settings.llm_debug:
            logger.info(
                "LLM request metadata: provider=%s model=%s active_resource_ids=%s",
                self.provider_name,
                self.model_name,
                extract_active_resource_ids(active_resource_catalog, allowed_resources=allowed_resources),
            )
        enrichment = self._enrich_uncached(
            patient,
            allowed_resources=allowed_resources,
            active_resource_catalog=active_resource_catalog,
        )
        self._write_cache(
            self.cache,
            patient,
            enrichment,
            allowed_resources=allowed_resources,
            active_resource_catalog=active_resource_catalog,
        )
        if settings.llm_debug:
            logger.info(
                "LLM response metadata: provider=%s model=%s required_resources=%s",
                self.provider_name,
                self.model_name,
                enrichment.required_resources,
            )
        return enrichment

    @abstractmethod
    def _enrich_uncached(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, Any] | None = None,
    ) -> ClinicalEnrichment:
        raise NotImplementedError


class UnavailableClinicalExtractor(ClinicalExtractor):
    def __init__(self, provider_name: str, model_name: str, error: Exception) -> None:
        super().__init__()
        self.provider_name = provider_name
        self.model_name = model_name
        self.error = error
        self._provider_requested = provider_name
        self._fallback_order = [provider_name]
        self._provider_attempts = {provider_name: {"successes": 0, "failures": 0}}
        self._provider_retries = {provider_name: 0}

    def enrich_patient(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, Any] | None = None,
    ) -> ClinicalEnrichment:
        raise self.error


class ChainedClinicalExtractor(ClinicalExtractor):
    def __init__(
        self,
        *,
        requested_provider: str,
        extractors: list[ClinicalExtractor],
        fallback_to_mock: bool = True,
        debug: bool = False,
    ) -> None:
        super().__init__()
        self.extractors = list(extractors)
        if fallback_to_mock and not any(extractor.provider_name == "mock" for extractor in self.extractors):
            self.extractors.append(MockClinicalExtractor())
        self._provider_requested = requested_provider
        self._fallback_order = [extractor.provider_name for extractor in self.extractors]
        self._fallback_to_mock = fallback_to_mock
        self._debug = debug
        self.provider_name = "unresolved"
        self.model_name = "unresolved"
        self._provider_attempts = {
            extractor.provider_name: {"successes": 0, "failures": 0} for extractor in self.extractors
        }
        self._provider_retries = {extractor.provider_name: 0 for extractor in self.extractors}

    def enrich_patient(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, Any] | None = None,
    ) -> ClinicalEnrichment:
        if not self.extractors:
            raise LLMExtractionError("No LLM providers were configured")

        last_error: Exception | None = None
        for index, extractor in enumerate(self.extractors):
            fallback_target = self.extractors[index + 1].provider_name if index + 1 < len(self.extractors) else None
            try:
                enrichment = extractor.enrich_patient(
                    patient,
                    allowed_resources=allowed_resources,
                    active_resource_catalog=active_resource_catalog,
                )
            except Exception as exc:
                self._provider_attempts[extractor.provider_name]["failures"] += 1
                if fallback_target is not None:
                    self._fallback_count += 1
                self._sync_child_metrics()
                self._log_provider_failure(
                    patient=patient,
                    extractor=extractor,
                    exc=exc,
                    fallback_target=fallback_target,
                    retry_attempted=getattr(extractor, "_last_retry_attempted", False),
                )
                last_error = exc
                continue

            self._provider_attempts[extractor.provider_name]["successes"] += 1
            self.provider_name = extractor.provider_name
            self.model_name = extractor.model_name
            self._sync_child_metrics()
            return enrichment

        self._sync_child_metrics()
        if last_error is not None:
            raise last_error
        raise LLMExtractionError("No LLM providers succeeded")

    def _sync_child_metrics(self) -> None:
        self._cache_hits = sum(extractor.cache_hits for extractor in self.extractors)
        self._cache_misses = sum(extractor.cache_misses for extractor in self.extractors)
        self._provider_retries = {
            extractor.provider_name: int(getattr(extractor, "_provider_retries", {}).get(extractor.provider_name, 0))
            for extractor in self.extractors
        }

    def _log_provider_failure(
        self,
        *,
        patient: Patient,
        extractor: ClinicalExtractor,
        exc: Exception,
        fallback_target: str | None,
        retry_attempted: bool,
    ) -> None:
        message = (
            "LLM provider failure: provider=%s model=%s complaint_len=%s "
            "description_len=%s exception_class=%s exception_message=%s fallback_target=%s retry_attempted=%s"
        )
        log_fn = logger.exception if self._debug else logger.warning
        log_fn(
            message,
            extractor.provider_name,
            extractor.model_name,
            len(patient.chief_complaint),
            len(patient.clinical_description),
            exc.__class__.__name__,
            str(exc),
            fallback_target or "none",
            retry_attempted,
        )


class MockClinicalExtractor(SingleProviderClinicalExtractor):
    def __init__(self, cache: ClinicalEnrichmentCache | None = None) -> None:
        super().__init__(cache=cache)
        self.provider_name = "mock"
        self.model_name = "mock"
        self._provider_requested = "mock"
        self._fallback_order = ["mock"]
        self._provider_attempts = {"mock": {"successes": 0, "failures": 0}}
        self._provider_retries = {"mock": 0}

    def enrich_patient(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, Any] | None = None,
    ) -> ClinicalEnrichment:
        enrichment = super().enrich_patient(
            patient,
            allowed_resources=allowed_resources,
            active_resource_catalog=active_resource_catalog,
        )
        self.provider_name = "mock"
        self._provider_attempts["mock"]["successes"] += 1
        return enrichment

    def _enrich_uncached(
        self,
        patient: Patient,
        *,
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, Any] | None = None,
    ) -> ClinicalEnrichment:
        text = f"{patient.chief_complaint} {patient.clinical_description}".lower()
        symptoms = self._extract_symptoms(text)
        category, risk, explanation_bits = self._classify(text, symptoms)
        deterioration_rate = self._deterioration_rate(risk, category)
        max_wait_time = self._max_wait_time(risk)
        estimated_service_time = self._estimated_service_time(risk, category)
        resources = self._infer_resources(
            text,
            risk,
            category,
            allowed_resources=allowed_resources,
        )

        return ClinicalEnrichment(
            key_symptoms=symptoms,
            textual_risk_score=risk,
            clinical_category=category,
            deterioration_rate=deterioration_rate,
            max_wait_time=max_wait_time,
            estimated_service_time=estimated_service_time,
            required_resources=resources,
            explanation="; ".join(explanation_bits),
        )

    def _extract_symptoms(self, text: str) -> list[str]:
        known_symptoms = [
            "chest pain",
            "dyspnea",
            "cold sweat",
            "severe bleeding",
            "trauma",
            "fever",
            "cough",
            "headache",
            "sore throat",
            "palpitations",
            "tachypnea",
            "collapse",
            "cardiac arrest",
            "confusion",
            "abdominal pain",
            "vomiting",
        ]
        symptoms = [symptom for symptom in known_symptoms if symptom in text]
        return symptoms or ["nonspecific symptoms"]

    def _classify(self, text: str, symptoms: list[str]) -> tuple[str, int, list[str]]:
        explanation_bits: list[str] = []
        if any(keyword in text for keyword in ("cardiac arrest", "collapse", "unresponsive")):
            explanation_bits.append("critical collapse pattern detected")
            return "cardiovascular", 5, explanation_bits
        if ("chest pain" in text and "cold sweat" in text) or ("chest pain" in text and "dyspnea" in text):
            explanation_bits.append("combined chest pain with autonomic or respiratory symptoms")
            return "cardiovascular", 4, explanation_bits
        if "chest pain" in text or "palpitations" in text:
            explanation_bits.append("cardiovascular warning symptoms detected")
            return "cardiovascular", 3, explanation_bits
        if "severe bleeding" in text:
            explanation_bits.append("severe bleeding implies major trauma burden")
            return "trauma", 5, explanation_bits
        if "trauma" in text:
            explanation_bits.append("trauma pattern detected")
            return "trauma", 4, explanation_bits
        if "fever" in text and "cough" in text:
            explanation_bits.append("infectious respiratory syndrome suspected")
            return "infectious", 3, explanation_bits
        if "fever" in text:
            explanation_bits.append("infectious syndrome suspected")
            return "infectious", 2, explanation_bits
        if any(keyword in text for keyword in ("vomiting", "dehydration", "glucose", "metabolic")):
            explanation_bits.append("possible metabolic or systemic imbalance")
            return "metabolic", 3, explanation_bits
        if "dyspnea" in text or "tachypnea" in text:
            explanation_bits.append("respiratory distress symptoms detected")
            return "respiratory", 4, explanation_bits
        if "mild headache" in text or "sore throat" in text:
            explanation_bits.append("mild low-acuity symptom pattern")
            return "minor", 1, explanation_bits
        explanation_bits.append(f"defaulted to undifferentiated review from symptoms: {', '.join(symptoms)}")
        return "unknown", 2, explanation_bits

    def _deterioration_rate(self, risk: int, category: str) -> float:
        base = {1: 0.01, 2: 0.025, 3: 0.05, 4: 0.08, 5: 0.12}[risk]
        if category in {"cardiovascular", "trauma", "respiratory"}:
            base += 0.01
        return round(base, 3)

    def _max_wait_time(self, risk: int) -> int:
        return {5: 0, 4: 10, 3: 30, 2: 60, 1: 120}[risk]

    def _estimated_service_time(self, risk: int, category: str) -> int:
        base = {1: 20, 2: 30, 3: 45, 4: 60, 5: 90}[risk]
        if category in {"cardiovascular", "trauma", "metabolic"}:
            base += 10
        return base

    def _infer_resources(
        self,
        text: str,
        risk: int,
        category: str,
        *,
        allowed_resources: list[str] | None = None,
    ) -> list[str]:
        allowed = {resource.strip().lower() for resource in (allowed_resources or []) if resource.strip()}
        if not allowed:
            allowed = {
                "doctor",
                "nurse",
                "observation_bed",
                "resuscitation_room",
                "vital_sign_monitor",
                "laboratory",
            }

        resources = ["doctor"]
        if risk >= 2 and "nurse" in allowed:
            resources.append("nurse")
        if risk >= 3 and "observation_bed" in allowed:
            resources.append("observation_bed")
        if risk >= 4 and "vital_sign_monitor" in allowed:
            resources.append("vital_sign_monitor")
        if risk == 5 and "resuscitation_room" in allowed:
            resources.append("resuscitation_room")
        if "laboratory" in allowed and category in {"cardiovascular", "infectious", "metabolic"}:
            resources.append("laboratory")
        elif "laboratory" in allowed and category == "trauma" and risk >= 4:
            resources.append("laboratory")
        elif "laboratory" in allowed and category == "unknown" and risk >= 4:
            resources.append("laboratory")
        if "xray_room" in allowed and (
            "trauma" in text
            or "fracture" in text
            or "fall" in text
            or "bone" in text
            or "chest injury" in text
        ):
            resources.append("xray_room")
        if "ct_scanner" in allowed and (
            "head trauma" in text
            or "neurological" in text
            or "stroke" in text
            or "seizure" in text
            or "altered mental status" in text
            or "confusion" in text
        ):
            resources.append("ct_scanner")
        if "ultrasound_room" in allowed and (
            "abdominal pain" in text
            or "pregnancy" in text
            or "pregnant" in text
            or "internal bleeding" in text
            or "pelvic pain" in text
        ):
            resources.append("ultrasound_room")
        if "isolation_room" in allowed and (
            ("fever" in text and "cough" in text)
            or "contagious" in text
            or "respiratory infection" in text
        ):
            resources.append("isolation_room")
        if "pharmacy" in allowed and (
            "overdose" in text
            or "toxicology" in text
            or "drug reaction" in text
            or "medication" in text
            or "poisoning" in text
        ):
            resources.append("pharmacy")
        if "specialist" in allowed and (
            ("stroke" in text or "seizure" in text or "neurological" in text)
            or (category in {"unknown", "cardiovascular", "trauma"} and risk >= 4)
        ):
            resources.append("specialist")
        deduped: list[str] = []
        seen: set[str] = set()
        for resource in resources:
            if resource not in allowed or resource in seen:
                continue
            seen.add(resource)
            deduped.append(resource)
        return deduped
