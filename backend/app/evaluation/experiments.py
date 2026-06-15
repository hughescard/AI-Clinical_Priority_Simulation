from __future__ import annotations

from pydantic import BaseModel, Field

from app.algorithms import get_algorithm, list_supported_algorithms
from app.config import settings
from app.evaluation.aggregation import aggregate_runs_by_algorithm
from app.evaluation.analysis import analyze_against_baseline
from app.models.simulation import (
    AdvancedScenarioConfig,
    SimulationConfig,
    SimulationResult,
    build_active_resource_catalog,
)
from app.simulation.simulator import ClinicalTriageSimulator


class ExperimentComparisonRequest(BaseModel):
    algorithms: list[str] = Field(min_length=1)
    scenario: str
    seed_start: int
    data_source: str = "synthetic"
    replications: int = Field(gt=0)
    duration_minutes: int = Field(gt=0, le=1440)
    advanced_config: AdvancedScenarioConfig | None = None


def run_experiment_comparison(request: ExperimentComparisonRequest) -> dict:
    supported_algorithms = set(list_supported_algorithms())
    invalid_algorithms = [algorithm for algorithm in request.algorithms if algorithm not in supported_algorithms]
    if invalid_algorithms:
        invalid_display = ", ".join(sorted(invalid_algorithms))
        raise ValueError(f"Unsupported algorithms: {invalid_display}")

    runs: list[dict] = []
    for algorithm_name in request.algorithms:
        for offset in range(request.replications):
            seed = request.seed_start + offset
            result = _run_single_simulation(
                algorithm_name=algorithm_name,
                scenario=request.scenario,
                seed=seed,
                data_source=request.data_source,
                duration_minutes=request.duration_minutes,
                advanced_config=request.advanced_config,
            )
            runs.append(
                {
                    "algorithm": algorithm_name,
                    "seed": seed,
                    "metrics": result.metrics,
                    "llm_provider_requested": result.llm_provider_requested,
                    "llm_provider_used": result.llm_provider_used,
                    "llm_fallback_order": result.llm_fallback_order,
                    "llm_fallback_count": result.llm_fallback_count,
                    "llm_cache_hits": result.llm_cache_hits,
                    "llm_cache_misses": result.llm_cache_misses,
                    "llm_provider_attempts": result.llm_provider_attempts,
                    "llm_provider_retries": result.llm_provider_retries,
                }
            )

    return {
        "scenario": request.scenario,
        "seed_start": request.seed_start,
        "replications": request.replications,
        "duration_minutes": request.duration_minutes,
        "data_source": request.data_source,
        "advanced_config": request.advanced_config.model_dump(mode="json") if request.advanced_config else None,
        "algorithms": request.algorithms,
        "results": aggregate_runs_by_algorithm(runs),
        "runs": runs,
    }


def run_experiment_analysis(request: ExperimentComparisonRequest, baseline_algorithm: str = "fifo") -> dict:
    comparison = run_experiment_comparison(request)
    analysis = analyze_against_baseline(comparison, baseline_algorithm=baseline_algorithm)
    return {
        "comparison": comparison,
        "analysis": analysis,
    }


def _run_single_simulation(
    *,
    algorithm_name: str,
    scenario: str,
    seed: int,
    data_source: str,
    duration_minutes: int,
    advanced_config: AdvancedScenarioConfig | None,
) -> SimulationResult:
    algorithm = get_algorithm(algorithm_name)
    capacities, active_catalog = build_active_resource_catalog(
        settings.default_resource_capacity.copy(),
        advanced_config,
    )
    config = SimulationConfig(
        algorithm=algorithm_name,
        scenario=scenario,
        seed=seed,
        data_source=data_source,
        duration_minutes=duration_minutes,
        doctor_round_interval_minutes=settings.doctor_round_interval_minutes,
        deterioration_interval_minutes=settings.deterioration_interval_minutes,
        resource_capacities=capacities,
        active_resource_catalog=active_catalog,
        advanced_config=advanced_config,
    )
    simulator = ClinicalTriageSimulator(config=config, algorithm=algorithm)
    return simulator.run()
