from __future__ import annotations

from app.config import settings
from app.llm.cache import (
    ClinicalEnrichmentCache,
    FileClinicalEnrichmentCache,
    InMemoryClinicalEnrichmentCache,
)
from app.llm.extractor import (
    ChainedClinicalExtractor,
    ClinicalExtractor,
    LLMExtractionError,
    MockClinicalExtractor,
    UnavailableClinicalExtractor,
)
from app.llm.mistral_extractor import MistralClinicalExtractor
from app.llm.ollama_extractor import OllamaClinicalExtractor

SUPPORTED_PROVIDERS = ("mock", "mistral", "ollama", "openai")


def build_cache(cache_path: str | None = None) -> ClinicalEnrichmentCache:
    if cache_path:
        return FileClinicalEnrichmentCache(cache_path)
    return InMemoryClinicalEnrichmentCache()


def get_clinical_extractor(
    provider: str | None = None,
    *,
    cache: ClinicalEnrichmentCache | None = None,
    provider_overrides: dict[str, ClinicalExtractor] | None = None,
) -> ClinicalExtractor:
    resolved_provider = (provider or settings.llm_provider).strip().lower()
    if resolved_provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported LLM provider: {resolved_provider}")

    resolved_cache = cache or build_cache(settings.llm_cache_path)
    overrides = provider_overrides or {}

    if resolved_provider == "mock":
        return overrides.get("mock") or MockClinicalExtractor(cache=resolved_cache)

    provider_order = _resolve_provider_order(resolved_provider)
    extractors: list[ClinicalExtractor] = []
    for provider_name in provider_order:
        extractor = overrides.get(provider_name) or _build_single_provider(provider_name, resolved_cache)
        extractors.append(extractor)

    return ChainedClinicalExtractor(
        requested_provider=resolved_provider,
        extractors=extractors,
        fallback_to_mock=settings.llm_fallback_to_mock,
        debug=settings.llm_debug,
    )


def _resolve_provider_order(requested_provider: str) -> list[str]:
    if requested_provider == "mock":
        return ["mock"]

    base_order = [requested_provider]
    for provider_name in settings.llm_fallback_order:
        if provider_name not in SUPPORTED_PROVIDERS:
            continue
        if provider_name == requested_provider:
            continue
        if provider_name == "mock" and not settings.llm_fallback_to_mock:
            continue
        base_order.append(provider_name)

    if settings.llm_fallback_to_mock and "mock" not in base_order:
        base_order.append("mock")

    deduped: list[str] = []
    for provider_name in base_order:
        if provider_name in deduped:
            continue
        deduped.append(provider_name)
    return deduped


def _build_single_provider(provider_name: str, cache: ClinicalEnrichmentCache) -> ClinicalExtractor:
    if provider_name == "mock":
        return MockClinicalExtractor(cache=cache)
    if provider_name == "mistral":
        api_key = settings.mistral_api_key
        if not api_key:
            return UnavailableClinicalExtractor(
                "mistral",
                settings.mistral_model,
                LLMExtractionError("MISTRAL_API_KEY is required when MISTRAL is in the provider chain"),
            )
        return MistralClinicalExtractor(
            api_key=api_key,
            model=settings.mistral_model,
            timeout_seconds=settings.mistral_timeout_seconds,
            cache=cache,
        )
    if provider_name == "ollama":
        return OllamaClinicalExtractor(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
            cache=cache,
        )
    if provider_name == "openai":
        api_key = settings.openai_api_key
        if not api_key:
            return UnavailableClinicalExtractor(
                "openai",
                settings.openai_model,
                LLMExtractionError("OPENAI_API_KEY is required when OPENAI is in the provider chain"),
            )
        return UnavailableClinicalExtractor(
            "openai",
            settings.openai_model,
            LLMExtractionError("OpenAI provider is not enabled in this backend build"),
        )
    raise ValueError(f"Unsupported LLM provider: {provider_name}")
