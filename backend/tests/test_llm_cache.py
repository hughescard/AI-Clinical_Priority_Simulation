from pathlib import Path

from app.llm.cache import FileClinicalEnrichmentCache, InMemoryClinicalEnrichmentCache, build_cache_key
from app.llm.extractor import MockClinicalExtractor
from app.models.patient import Patient


def build_patient() -> Patient:
    return Patient(
        patient_id="P001",
        age=45,
        arrival_time=0,
        chief_complaint="Chest pain",
        clinical_description="Chest pain with cold sweat",
        risk_level=3,
        current_risk=3.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=30,
        required_resources=[],
    )


def test_in_memory_cache_returns_same_enrichment_for_same_text() -> None:
    cache = InMemoryClinicalEnrichmentCache()
    extractor = MockClinicalExtractor(cache=cache)
    patient = build_patient()
    first = extractor.enrich_patient(patient)
    second = extractor.enrich_patient(patient)
    assert first == second


def test_file_cache_recovers_from_invalid_json(tmp_path: Path) -> None:
    cache_path = tmp_path / "clinical_cache.json"
    cache_path.write_text("{not-valid-json", encoding="utf-8")
    cache = FileClinicalEnrichmentCache(cache_path)
    extractor = MockClinicalExtractor(cache=cache)

    enrichment = extractor.enrich_patient(build_patient())
    cached = cache.get("Chest pain", "Chest pain with cold sweat")

    assert cached == enrichment


def test_cache_key_isolated_by_provider_and_model() -> None:
    cache = InMemoryClinicalEnrichmentCache()
    extractor = MockClinicalExtractor(cache=cache)
    enrichment = extractor.enrich_patient(build_patient())

    cache.set(
        "Chest pain",
        "Chest pain with cold sweat",
        enrichment,
        provider="mistral",
        model="mistral-small-latest",
    )

    mock_cached = cache.get("Chest pain", "Chest pain with cold sweat", provider="mock", model="mock")
    mistral_cached = cache.get(
        "Chest pain",
        "Chest pain with cold sweat",
        provider="mistral",
        model="mistral-small-latest",
    )

    assert mock_cached == enrichment
    assert mistral_cached == enrichment


def test_cache_key_changes_when_active_resource_catalog_changes() -> None:
    key_with_ct = build_cache_key(
        "Head trauma",
        "Head trauma with confusion",
        provider="mistral",
        model="mistral-small-latest",
        allowed_resources=["doctor", "ct_scanner"],
        active_resource_catalog={
            "doctor": {"id": "doctor", "capacity": 2, "enabled": True},
            "ct_scanner": {"id": "ct_scanner", "capacity": 1, "enabled": True},
        },
    )
    key_without_ct = build_cache_key(
        "Head trauma",
        "Head trauma with confusion",
        provider="mistral",
        model="mistral-small-latest",
        allowed_resources=["doctor"],
        active_resource_catalog={
            "doctor": {"id": "doctor", "capacity": 2, "enabled": True},
        },
    )

    assert key_with_ct != key_without_ct


def test_cache_key_differs_between_zero_and_positive_capacity() -> None:
    zero_capacity_key = build_cache_key(
        "Head trauma",
        "Head trauma with confusion",
        provider="mistral",
        model="mistral-small-latest",
        allowed_resources=["doctor", "ct_scanner"],
        active_resource_catalog={
            "doctor": {"id": "doctor", "capacity": 2, "enabled": True},
            "ct_scanner": {"id": "ct_scanner", "capacity": 0, "enabled": True},
        },
    )
    positive_capacity_key = build_cache_key(
        "Head trauma",
        "Head trauma with confusion",
        provider="mistral",
        model="mistral-small-latest",
        allowed_resources=["doctor", "ct_scanner"],
        active_resource_catalog={
            "doctor": {"id": "doctor", "capacity": 2, "enabled": True},
            "ct_scanner": {"id": "ct_scanner", "capacity": 1, "enabled": True},
        },
    )

    assert zero_capacity_key != positive_capacity_key


def test_cache_key_isolated_by_allowed_resource_catalog() -> None:
    cache = InMemoryClinicalEnrichmentCache()
    extractor = MockClinicalExtractor(cache=cache)
    patient = build_patient()

    default_enrichment = extractor.enrich_patient(patient, allowed_resources=["doctor", "nurse", "laboratory"])
    limited_enrichment = extractor.enrich_patient(patient, allowed_resources=["doctor"])

    cached_default = cache.get(
        "Chest pain",
        "Chest pain with cold sweat",
        provider="mock",
        model="mock",
        allowed_resources=["doctor", "nurse", "laboratory"],
    )
    cached_limited = cache.get(
        "Chest pain",
        "Chest pain with cold sweat",
        provider="mock",
        model="mock",
        allowed_resources=["doctor"],
    )

    assert cached_default == default_enrichment
    assert cached_limited == limited_enrichment
    assert cached_default is not None
    assert cached_limited is not None
    assert cached_default.required_resources != cached_limited.required_resources
