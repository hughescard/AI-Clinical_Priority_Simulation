from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from app.llm.schemas import ClinicalEnrichment
from app.llm.prompts import normalize_active_resource_catalog


class ClinicalEnrichmentCache(Protocol):
    def get(
        self,
        chief_complaint: str,
        clinical_description: str,
        *,
        provider: str = "mock",
        model: str = "mock",
        schema_version: str = "clinical_enrichment_v1",
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ) -> ClinicalEnrichment | None:
        raise NotImplementedError

    def set(
        self,
        chief_complaint: str,
        clinical_description: str,
        enrichment: ClinicalEnrichment,
        *,
        provider: str = "mock",
        model: str = "mock",
        schema_version: str = "clinical_enrichment_v1",
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ) -> None:
        raise NotImplementedError


def build_cache_key(
    chief_complaint: str,
    clinical_description: str,
    *,
    provider: str = "mock",
    model: str = "mock",
    schema_version: str = "clinical_enrichment_v1",
    allowed_resources: list[str] | None = None,
    active_resource_catalog: dict[str, object] | None = None,
) -> str:
    normalized_resources = ",".join(sorted({resource.strip().lower() for resource in allowed_resources or [] if resource.strip()}))
    normalized_catalog = normalize_active_resource_catalog(
        active_resource_catalog,
        allowed_resources=allowed_resources,
    )
    catalog_signature = "|".join(
        f"{entry['id']}:{entry['capacity']}:{int(bool(entry['enabled']))}" for entry in normalized_catalog
    )
    normalized = "||".join(
        [
            provider.strip().lower(),
            model.strip().lower(),
            schema_version.strip().lower(),
            normalized_resources,
            catalog_signature,
            chief_complaint.strip().lower(),
            clinical_description.strip().lower(),
        ]
    )
    return sha256(normalized.encode("utf-8")).hexdigest()


class InMemoryClinicalEnrichmentCache:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def get(
        self,
        chief_complaint: str,
        clinical_description: str,
        *,
        provider: str = "mock",
        model: str = "mock",
        schema_version: str = "clinical_enrichment_v1",
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ) -> ClinicalEnrichment | None:
        payload = self._store.get(
            build_cache_key(
                chief_complaint,
                clinical_description,
                provider=provider,
                model=model,
                schema_version=schema_version,
                allowed_resources=allowed_resources,
                active_resource_catalog=active_resource_catalog,
            )
        )
        return ClinicalEnrichment.model_validate(payload) if payload else None

    def set(
        self,
        chief_complaint: str,
        clinical_description: str,
        enrichment: ClinicalEnrichment,
        *,
        provider: str = "mock",
        model: str = "mock",
        schema_version: str = "clinical_enrichment_v1",
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ) -> None:
        self._store[
            build_cache_key(
                chief_complaint,
                clinical_description,
                provider=provider,
                model=model,
                schema_version=schema_version,
                allowed_resources=allowed_resources,
                active_resource_catalog=active_resource_catalog,
            )
        ] = enrichment.model_dump()


class FileClinicalEnrichmentCache:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def get(
        self,
        chief_complaint: str,
        clinical_description: str,
        *,
        provider: str = "mock",
        model: str = "mock",
        schema_version: str = "clinical_enrichment_v1",
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ) -> ClinicalEnrichment | None:
        payload = self._read_all()
        entry = payload.get(
            build_cache_key(
                chief_complaint,
                clinical_description,
                provider=provider,
                model=model,
                schema_version=schema_version,
                allowed_resources=allowed_resources,
                active_resource_catalog=active_resource_catalog,
            )
        )
        return ClinicalEnrichment.model_validate(entry) if entry else None

    def set(
        self,
        chief_complaint: str,
        clinical_description: str,
        enrichment: ClinicalEnrichment,
        *,
        provider: str = "mock",
        model: str = "mock",
        schema_version: str = "clinical_enrichment_v1",
        allowed_resources: list[str] | None = None,
        active_resource_catalog: dict[str, object] | None = None,
    ) -> None:
        payload = self._read_all()
        payload[
            build_cache_key(
                chief_complaint,
                clinical_description,
                provider=provider,
                model=model,
                schema_version=schema_version,
                allowed_resources=allowed_resources,
                active_resource_catalog=active_resource_catalog,
            )
        ] = enrichment.model_dump()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _read_all(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return raw if isinstance(raw, dict) else {}
