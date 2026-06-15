from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _running_inside_docker() -> bool:
    return Path("/.dockerenv").exists()


def _default_ollama_base_url() -> str:
    return "http://ollama:11434" if _running_inside_docker() else "http://localhost:11434"


class Settings(BaseModel):
    app_name: str = "clinical-triage-simulator"
    default_duration_minutes: int = 480
    deterioration_interval_minutes: int = 15
    doctor_round_interval_minutes: int = 15
    doctor_round_base_duration_minutes: float = 0.5
    doctor_round_time_per_waiting_patient_minutes: float = 0.1
    max_timeline_events: int = 5000
    default_seed: int = 42
    default_resource_capacity: dict[str, int] = Field(
        default_factory=lambda: {
            "doctor": 3,
            "nurse": 4,
            "observation_bed": 6,
            "resuscitation_room": 1,
            "vital_sign_monitor": 4,
            "laboratory": 2,
        }
    )

    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "mock").strip().lower()

    @property
    def llm_fallback_order(self) -> list[str]:
        raw_value = os.getenv("LLM_FALLBACK_ORDER", "ollama,mock")
        return [item.strip().lower() for item in raw_value.split(",") if item.strip()]

    @property
    def mistral_api_key(self) -> str | None:
        value = os.getenv("MISTRAL_API_KEY")
        return value.strip() if value else None

    @property
    def mistral_model(self) -> str:
        return os.getenv("MISTRAL_MODEL", "mistral-small-latest").strip()

    @property
    def mistral_timeout_seconds(self) -> float:
        raw_value = os.getenv("MISTRAL_TIMEOUT_SECONDS", "30").strip()
        return float(raw_value)

    @property
    def ollama_base_url(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", _default_ollama_base_url()).strip()

    @property
    def ollama_model(self) -> str:
        return os.getenv("OLLAMA_MODEL", "llama3.2:3b").strip()

    @property
    def ollama_timeout_seconds(self) -> float:
        raw_value = os.getenv("OLLAMA_TIMEOUT_SECONDS", "30").strip()
        return float(raw_value)

    @property
    def openai_api_key(self) -> str | None:
        value = os.getenv("OPENAI_API_KEY")
        return value.strip() if value else None

    @property
    def openai_model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

    @property
    def openai_timeout_seconds(self) -> float:
        raw_value = os.getenv("OPENAI_TIMEOUT_SECONDS", "30").strip()
        return float(raw_value)

    @property
    def llm_fallback_to_mock(self) -> bool:
        return _get_bool_env("LLM_FALLBACK_TO_MOCK", True)

    @property
    def llm_debug(self) -> bool:
        return _get_bool_env("LLM_DEBUG", False)

    @property
    def llm_cache_path(self) -> str | None:
        value = os.getenv("LLM_CACHE_PATH")
        return value.strip() if value else None


settings = Settings()
