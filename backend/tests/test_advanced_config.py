from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import ValidationError

from app.api.experiment_routes import export_experiments_json
from app.api.simulation_routes import SimulationRequest, export_simulation_json, run_simulation
from app.config import settings
from app.evaluation.experiments import ExperimentComparisonRequest
from app.models.simulation import AdvancedScenarioConfig, ResourceCatalogEntry
from app.simulation.scenario_generator import ScenarioGenerator


def build_advanced_config() -> AdvancedScenarioConfig:
    return AdvancedScenarioConfig(
        resources=[
            ResourceCatalogEntry(id="doctor", capacity=2, enabled=True),
            ResourceCatalogEntry(id="nurse", capacity=0, enabled=False),
            ResourceCatalogEntry(id="ct_scanner", capacity=1, enabled=True),
        ]
    )


def test_advanced_config_rejects_duplicate_resource_ids() -> None:
    with pytest.raises(ValidationError):
        AdvancedScenarioConfig(
            resources=[
                ResourceCatalogEntry(id="doctor", capacity=1, enabled=True),
                ResourceCatalogEntry(id="doctor", capacity=2, enabled=True),
            ]
        )


def test_advanced_config_rejects_invalid_resource_id() -> None:
    with pytest.raises(ValidationError):
        ResourceCatalogEntry(id="Doctor Room", capacity=1, enabled=True)


def test_simulation_advanced_config_overrides_resource_catalog() -> None:
    result = asyncio.run(
        run_simulation(
            SimulationRequest(
                algorithm="fifo",
                scenario="normal",
                seed=42,
                duration_minutes=120,
                advanced_config=build_advanced_config(),
            )
        )
    )

    assert result.active_resource_catalog["doctor"]["capacity"] == 2
    assert result.active_resource_catalog["nurse"]["enabled"] is False
    assert result.resource_summary["nurse"]["capacity"] == 0
    assert result.active_resource_catalog["ct_scanner"]["enabled"] is True
    assert result.resource_summary["ct_scanner"]["capacity"] == 1
    assert result.advanced_config is not None


def test_scenario_generation_with_advanced_config_is_deterministic() -> None:
    advanced_config = build_advanced_config()
    first_patients, first_resources = ScenarioGenerator(
        seed=42,
        base_resource_capacities=settings.default_resource_capacity.copy(),
        advanced_config=advanced_config,
    ).generate("normal", 240)
    second_patients, second_resources = ScenarioGenerator(
        seed=42,
        base_resource_capacities=settings.default_resource_capacity.copy(),
        advanced_config=advanced_config,
    ).generate("normal", 240)

    assert first_patients == second_patients
    assert first_resources == second_resources
    assert "ct_scanner" in first_resources


def test_simulation_json_export_includes_advanced_config_and_active_resource_catalog() -> None:
    response = asyncio.run(
        export_simulation_json(
            SimulationRequest(
                algorithm="fifo",
                scenario="normal",
                seed=42,
                duration_minutes=120,
                advanced_config=build_advanced_config(),
            )
        )
    )
    payload = json.loads(response.body.decode("utf-8"))

    assert payload["request"]["advanced_config"]["resources"][2]["id"] == "ct_scanner"
    assert payload["result"]["active_resource_catalog"]["ct_scanner"]["capacity"] == 1
    assert payload["result"]["advanced_config"]["resources"][1]["enabled"] is False


def test_experiment_json_export_includes_advanced_config() -> None:
    response = asyncio.run(
        export_experiments_json(
            ExperimentComparisonRequest(
                algorithms=["fifo"],
                scenario="normal",
                seed_start=42,
                replications=1,
                duration_minutes=120,
                advanced_config=build_advanced_config(),
            )
        )
    )
    payload = json.loads(response.body.decode("utf-8"))

    assert payload["request"]["advanced_config"]["resources"][0]["id"] == "doctor"
    assert payload["result"]["runs"][0]["algorithm"] == "fifo"
