from __future__ import annotations

import json
import os
import platform
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.evaluation.analysis import analyze_against_baseline
from app.evaluation.aggregation import AGGREGATED_METRICS
from app.evaluation.export import rows_to_csv
from app.evaluation.experiments import ExperimentComparisonRequest, run_experiment_comparison
from app.models.simulation import AdvancedScenarioConfig, ResourceCatalogEntry

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "experiments" / "results" / "final_validation"
DEFAULT_FINAL_ALGORITHMS = ["fifo", "greedy", "astar", "cpsat", "simulated_annealing"]
DEFAULT_FINAL_SCENARIOS = ["normal", "high_demand", "limited_resources"]
QUICK_MODE_ALGORITHMS = ["greedy", "cpsat", "simulated_annealing"]
QUICK_MODE_SCENARIOS = ["high_demand"]
QUICK_MODE_DURATION_MINUTES = 120
QUICK_MODE_REPLICATIONS = 2
FINAL_SUMMARY_FIELDS = ["scenario", "algorithm", "metric_name", "mean", "std", "min", "max", "replications"]
FINAL_METRIC_RANKING_FIELDS = [
    "scenario",
    "metric_name",
    "display_label",
    "direction",
    "rank",
    "algorithm",
    "mean",
    "std",
    "min",
    "max",
    "practical_tie_group",
]
FINAL_ALGORITHM_RANKING_FIELDS = [
    "scenario",
    "ranking_type",
    "rank",
    "algorithm",
    "score_name",
    "score_value",
    "first_place_metrics",
    "tied_first_place_metrics",
]
ADVANCED_RESOURCE_PRESET = [
    ("doctor", 2),
    ("nurse", 4),
    ("observation_bed", 4),
    ("resuscitation_room", 1),
    ("vital_sign_monitor", 3),
    ("laboratory", 2),
    ("xray_room", 1),
    ("ct_scanner", 1),
    ("ultrasound_room", 1),
    ("isolation_room", 1),
    ("pharmacy", 1),
    ("specialist", 1),
]


@dataclass(frozen=True)
class FinalValidationConfig:
    algorithms: list[str]
    scenarios: list[str]
    data_source: str
    seed_start: int
    replications: int
    duration_minutes: int
    llm_provider: str
    llm_fallback_order: list[str]
    llm_fallback_to_mock: bool
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: float
    cache_path: str
    use_advanced_resources: bool
    output_dir: Path
    quick_mode: bool
    fail_on_llm_fallback: bool
    max_llm_fallbacks: int


def running_inside_docker() -> bool:
    return Path("/.dockerenv").exists()


def default_ollama_base_url() -> str:
    return "http://ollama:11434" if running_inside_docker() else "http://localhost:11434"


def default_final_cache_path() -> str:
    if running_inside_docker():
        return "/app/data/processed/llm_cache_final_ollama.json"
    return str(REPO_ROOT / "data" / "processed" / "llm_cache_final_ollama.json")


def build_advanced_resource_config() -> AdvancedScenarioConfig:
    return AdvancedScenarioConfig(
        resources=[
            ResourceCatalogEntry(id=resource_id, capacity=capacity, enabled=True)
            for resource_id, capacity in ADVANCED_RESOURCE_PRESET
        ]
    )


def normalize_csv_list(raw_value: str | None, default_values: list[str]) -> list[str]:
    if not raw_value:
        return list(default_values)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def resolve_run_configuration(
    *,
    quick_mode: bool,
    algorithms: list[str] | None,
    scenarios: list[str] | None,
    replications: int | None,
    duration_minutes: int | None,
    data_source: str,
    seed_start: int,
    llm_provider: str | None,
    llm_fallback_order: list[str] | None,
    llm_fallback_to_mock: bool,
    ollama_base_url: str | None,
    ollama_model: str | None,
    ollama_timeout_seconds: float | None,
    cache_path: str | None,
    use_advanced_resources: bool,
    output_dir: Path | None,
    fail_on_llm_fallback: bool,
    max_llm_fallbacks: int | None,
) -> FinalValidationConfig:
    resolved_provider = (llm_provider or os.getenv("LLM_PROVIDER") or "ollama").strip().lower()
    resolved_fallback_order = (
        list(llm_fallback_order)
        if llm_fallback_order is not None
        else normalize_csv_list(os.getenv("LLM_FALLBACK_ORDER"), ["ollama", "mock"])
    )
    resolved_base_url = (ollama_base_url or os.getenv("OLLAMA_BASE_URL") or default_ollama_base_url()).strip()
    resolved_model = (ollama_model or os.getenv("OLLAMA_MODEL") or "llama3.2:3b").strip()
    resolved_timeout = float(ollama_timeout_seconds or os.getenv("OLLAMA_TIMEOUT_SECONDS") or 30)
    resolved_cache_path = (cache_path or os.getenv("LLM_CACHE_PATH") or default_final_cache_path()).strip()
    resolved_max_fallbacks = 0 if fail_on_llm_fallback else int(max_llm_fallbacks if max_llm_fallbacks is not None else 1_000_000)
    if fail_on_llm_fallback and resolved_max_fallbacks != 0:
        raise ValueError("When --fail-on-llm-fallback is set, max fallbacks must be 0")

    if quick_mode:
        resolved_algorithms = list(QUICK_MODE_ALGORITHMS)
        resolved_scenarios = list(QUICK_MODE_SCENARIOS)
        resolved_replications = QUICK_MODE_REPLICATIONS
        resolved_duration = QUICK_MODE_DURATION_MINUTES
    else:
        resolved_algorithms = list(algorithms or DEFAULT_FINAL_ALGORITHMS)
        resolved_scenarios = list(scenarios or DEFAULT_FINAL_SCENARIOS)
        resolved_replications = int(replications or 10)
        resolved_duration = int(duration_minutes or 480)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    resolved_output_dir = output_dir or (
        DEFAULT_OUTPUT_ROOT / f"{timestamp}_{resolved_provider}_{data_source}"
    )

    return FinalValidationConfig(
        algorithms=resolved_algorithms,
        scenarios=resolved_scenarios,
        data_source=data_source,
        seed_start=seed_start,
        replications=resolved_replications,
        duration_minutes=resolved_duration,
        llm_provider=resolved_provider,
        llm_fallback_order=resolved_fallback_order,
        llm_fallback_to_mock=llm_fallback_to_mock,
        ollama_base_url=resolved_base_url,
        ollama_model=resolved_model,
        ollama_timeout_seconds=resolved_timeout,
        cache_path=resolved_cache_path,
        use_advanced_resources=use_advanced_resources,
        output_dir=resolved_output_dir,
        quick_mode=quick_mode,
        fail_on_llm_fallback=fail_on_llm_fallback,
        max_llm_fallbacks=resolved_max_fallbacks,
    )


def validate_ollama_configuration(
    *,
    base_url: str,
    model: str,
    timeout_seconds: float,
    client: Any | None = None,
) -> dict[str, Any]:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"OLLAMA_BASE_URL is invalid: {base_url}")
    if not model.strip():
        raise ValueError("OLLAMA_MODEL must not be empty")

    owned_client = client is None
    http_client = client or httpx.Client(timeout=timeout_seconds)
    try:
        response = http_client.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise ValueError(f"Ollama reachability check failed for {base_url}: {exc}") from exc
    finally:
        if owned_client:
            http_client.close()

    models = payload.get("models", []) if isinstance(payload, dict) else []
    available_models = [
        str(item.get("name")).strip()
        for item in models
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    ]
    return {
        "provider": "ollama",
        "base_url": base_url.rstrip("/"),
        "model": model.strip(),
        "timeout_seconds": float(timeout_seconds),
        "reachable": True,
        "available_models": available_models,
    }


def validate_provider_configuration(
    config: FinalValidationConfig,
    *,
    client: Any | None = None,
) -> dict[str, Any]:
    if config.llm_provider == "mock":
        return {
            "provider": "mock",
            "reachable": True,
            "api_key_required": False,
            "note": "Deterministic mock provider requires no external service.",
        }
    if config.llm_provider == "ollama":
        return validate_ollama_configuration(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
            timeout_seconds=config.ollama_timeout_seconds,
            client=client,
        )
    if config.llm_provider == "mistral":
        if not os.getenv("MISTRAL_API_KEY", "").strip():
            raise ValueError("MISTRAL_API_KEY is required when --llm-provider mistral is selected")
        if not os.getenv("MISTRAL_MODEL", settings.mistral_model).strip():
            raise ValueError("MISTRAL_MODEL must not be empty")
        return {
            "provider": "mistral",
            "model": os.getenv("MISTRAL_MODEL", settings.mistral_model).strip(),
            "api_key_required": True,
            "api_key_configured": True,
        }
    if config.llm_provider == "openai":
        if not os.getenv("OPENAI_API_KEY", "").strip():
            raise ValueError("OPENAI_API_KEY is required when --llm-provider openai is selected")
        if not os.getenv("OPENAI_MODEL", settings.openai_model).strip():
            raise ValueError("OPENAI_MODEL must not be empty")
        return {
            "provider": "openai",
            "model": os.getenv("OPENAI_MODEL", settings.openai_model).strip(),
            "api_key_required": True,
            "api_key_configured": True,
        }
    raise ValueError(f"Unsupported llm provider: {config.llm_provider}")


@contextmanager
def temporary_llm_environment(config: FinalValidationConfig) -> Iterator[None]:
    updates = {
        "LLM_PROVIDER": config.llm_provider,
        "LLM_FALLBACK_ORDER": ",".join(config.llm_fallback_order),
        "LLM_FALLBACK_TO_MOCK": "true" if config.llm_fallback_to_mock else "false",
        "LLM_CACHE_PATH": config.cache_path,
        "OLLAMA_BASE_URL": config.ollama_base_url,
        "OLLAMA_MODEL": config.ollama_model,
        "OLLAMA_TIMEOUT_SECONDS": str(config.ollama_timeout_seconds),
    }
    previous = {key: os.getenv(key) for key in updates}
    for key, value in updates.items():
        os.environ[key] = value
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_final_validation(config: FinalValidationConfig) -> dict[str, Any]:
    advanced_config = build_advanced_resource_config() if config.use_advanced_resources else None
    results_by_scenario: dict[str, Any] = {}
    analyses_by_scenario: dict[str, Any] = {}
    for scenario in config.scenarios:
        request = ExperimentComparisonRequest(
            algorithms=config.algorithms,
            scenario=scenario,
            seed_start=config.seed_start,
            data_source=config.data_source,
            replications=config.replications,
            duration_minutes=config.duration_minutes,
            advanced_config=advanced_config,
        )
        comparison = run_experiment_comparison(request)
        analysis = analyze_against_baseline(comparison, baseline_algorithm="fifo")
        results_by_scenario[scenario] = comparison
        analyses_by_scenario[scenario] = analysis
    return {
        "advanced_config": advanced_config.model_dump(mode="json") if advanced_config else None,
        "results_by_scenario": results_by_scenario,
        "analyses_by_scenario": analyses_by_scenario,
        "overall_algorithm_summary": build_overall_algorithm_summary(analyses_by_scenario),
    }


def build_summary_rows(results_by_scenario: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario, result in results_by_scenario.items():
        replications = int(result.get("replications", 0))
        for algorithm, metrics in result.get("results", {}).items():
            for metric_name in AGGREGATED_METRICS:
                summary = metrics.get(metric_name, {})
                rows.append(
                    {
                        "scenario": scenario,
                        "algorithm": algorithm,
                        "metric_name": metric_name,
                        "mean": summary.get("mean", 0.0),
                        "std": summary.get("std", 0.0),
                        "min": summary.get("min", 0.0),
                        "max": summary.get("max", 0.0),
                        "replications": replications,
                    }
                )
    return rows


def build_metric_ranking_rows(analyses_by_scenario: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario, analysis in analyses_by_scenario.items():
        for ranking in analysis.get("per_metric_rankings", []):
            for item in ranking.get("ranking", []):
                rows.append(
                    {
                        "scenario": scenario,
                        "metric_name": ranking.get("metric_name"),
                        "display_label": ranking.get("display_label"),
                        "direction": ranking.get("direction"),
                        "rank": item.get("rank"),
                        "algorithm": item.get("algorithm"),
                        "mean": item.get("mean"),
                        "std": item.get("std"),
                        "min": item.get("min"),
                        "max": item.get("max"),
                        "practical_tie_group": item.get("practical_tie_group"),
                    }
                )
    return rows


def build_algorithm_ranking_rows(analyses_by_scenario: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ranking_sections = (
        ("balanced_overall_ranking", "balanced"),
        ("clinical_ranking", "clinical"),
        ("operational_ranking", "operational"),
        ("computational_ranking", "computational"),
    )
    for scenario, analysis in analyses_by_scenario.items():
        for key, ranking_type in ranking_sections:
            section = analysis.get(key, [])
            ranking_rows = section.get("ranking", []) if isinstance(section, dict) else section
            for item in ranking_rows:
                score_name = "balanced_score" if ranking_type == "balanced" else "total_score"
                rows.append(
                    {
                        "scenario": scenario,
                        "ranking_type": ranking_type,
                        "rank": item.get("rank"),
                        "algorithm": item.get("algorithm"),
                        "score_name": score_name,
                        "score_value": item.get(score_name, 0),
                        "first_place_metrics": item.get("first_place_metrics", 0),
                        "tied_first_place_metrics": item.get("tied_first_place_metrics", 0),
                    }
                )
    for item in build_overall_algorithm_summary(analyses_by_scenario):
        rows.append(
            {
                "scenario": "__overall__",
                "ranking_type": "balanced",
                "rank": item["rank"],
                "algorithm": item["algorithm"],
                "score_name": "average_rank",
                "score_value": item["average_rank"],
                "first_place_metrics": item["first_place_finishes"],
                "tied_first_place_metrics": item["best_rank"],
            }
        )
    return rows


def build_overall_algorithm_summary(analyses_by_scenario: dict[str, Any]) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, float | int]] = {}
    scenario_count = max(1, len(analyses_by_scenario))
    for analysis in analyses_by_scenario.values():
        for row in analysis.get("balanced_overall_ranking", []):
            algorithm = str(row["algorithm"])
            entry = totals.setdefault(
                algorithm,
                {
                    "algorithm": algorithm,
                    "rank_sum": 0.0,
                    "balanced_score_sum": 0.0,
                    "scenario_count": 0,
                    "first_place_finishes": 0,
                    "best_rank": 9999,
                },
            )
            rank = int(row.get("rank", 0))
            entry["rank_sum"] += rank
            entry["balanced_score_sum"] += float(row.get("balanced_score", 0.0))
            entry["scenario_count"] += 1
            if rank == 1:
                entry["first_place_finishes"] += 1
            entry["best_rank"] = min(int(entry["best_rank"]), rank)

    rows = []
    for entry in totals.values():
        scenarios_seen = max(1, int(entry["scenario_count"]))
        rows.append(
            {
                "algorithm": entry["algorithm"],
                "average_rank": round(float(entry["rank_sum"]) / scenario_count, 4),
                "average_balanced_score": round(float(entry["balanced_score_sum"]) / scenarios_seen, 6),
                "first_place_finishes": int(entry["first_place_finishes"]),
                "best_rank": int(entry["best_rank"]),
            }
        )
    rows.sort(
        key=lambda item: (
            float(item["average_rank"]),
            -float(item["average_balanced_score"]),
            -int(item["first_place_finishes"]),
            item["algorithm"],
        )
    )
    for index, item in enumerate(rows, start=1):
        item["rank"] = index
    return rows


def build_llm_usage_summary(results_by_scenario: dict[str, Any]) -> dict[str, Any]:
    usage = {
        "total_runs": 0,
        "provider_requested_counts": {},
        "provider_used_counts": {},
        "total_fallback_count": 0,
        "total_cache_hits": 0,
        "total_cache_misses": 0,
        "provider_attempt_totals": {},
        "provider_retry_totals": {},
        "per_scenario": {},
    }
    for scenario, result in results_by_scenario.items():
        scenario_usage = {
            "runs": 0,
            "provider_used_counts": {},
            "total_fallback_count": 0,
            "total_cache_hits": 0,
            "total_cache_misses": 0,
        }
        for run in result.get("runs", []):
            usage["total_runs"] += 1
            scenario_usage["runs"] += 1

            requested = run.get("llm_provider_requested")
            used = run.get("llm_provider_used")
            if requested:
                usage["provider_requested_counts"][requested] = usage["provider_requested_counts"].get(requested, 0) + 1
            if used:
                usage["provider_used_counts"][used] = usage["provider_used_counts"].get(used, 0) + 1
                scenario_usage["provider_used_counts"][used] = scenario_usage["provider_used_counts"].get(used, 0) + 1

            fallback_count = int(run.get("llm_fallback_count", 0) or 0)
            cache_hits = int(run.get("llm_cache_hits", 0) or 0)
            cache_misses = int(run.get("llm_cache_misses", 0) or 0)
            usage["total_fallback_count"] += fallback_count
            usage["total_cache_hits"] += cache_hits
            usage["total_cache_misses"] += cache_misses
            scenario_usage["total_fallback_count"] += fallback_count
            scenario_usage["total_cache_hits"] += cache_hits
            scenario_usage["total_cache_misses"] += cache_misses

            for provider_name, attempt in (run.get("llm_provider_attempts") or {}).items():
                summary = usage["provider_attempt_totals"].setdefault(provider_name, {"successes": 0, "failures": 0})
                summary["successes"] += int(attempt.get("successes", 0))
                summary["failures"] += int(attempt.get("failures", 0))
            for provider_name, retry_count in (run.get("llm_provider_retries") or {}).items():
                usage["provider_retry_totals"][provider_name] = usage["provider_retry_totals"].get(provider_name, 0) + int(
                    retry_count or 0
                )
        usage["per_scenario"][scenario] = scenario_usage
    return usage


def evaluate_report_validity(config: FinalValidationConfig, llm_usage_summary: dict[str, Any]) -> dict[str, Any]:
    total_fallback_count = int(llm_usage_summary.get("total_fallback_count", 0) or 0)
    report_valid = total_fallback_count <= config.max_llm_fallbacks
    warning = None
    if not report_valid:
        warning = (
            "LLM fallback occurred during final validation. Results are not report-valid. "
            "Increase timeout, improve provider reliability, or rerun with a clean cache."
        )
    elif total_fallback_count > 0:
        warning = (
            "LLM fallback occurred during final validation. Results completed, but they are not suitable "
            "for final report claims about real-provider behavior."
        )
    return {
        "report_valid_llm_run": total_fallback_count == 0,
        "total_fallback_count": total_fallback_count,
        "max_llm_fallbacks_allowed": config.max_llm_fallbacks,
        "within_allowed_fallback_limit": report_valid,
        "warning": warning,
    }


def build_protocol(config: FinalValidationConfig, *, cache_reused: bool, validity: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "algorithms": config.algorithms,
        "scenarios": config.scenarios,
        "data_source": config.data_source,
        "seed_start": config.seed_start,
        "replications": config.replications,
        "duration_minutes": config.duration_minutes,
        "llm_provider": config.llm_provider,
        "llm_fallback_order": config.llm_fallback_order,
        "llm_fallback_to_mock": config.llm_fallback_to_mock,
        "ollama_base_url": config.ollama_base_url,
        "ollama_model": config.ollama_model,
        "ollama_timeout_seconds": config.ollama_timeout_seconds,
        "llm_cache_path": config.cache_path,
        "llm_cache_reused": cache_reused,
        "fail_on_llm_fallback": config.fail_on_llm_fallback,
        "max_llm_fallbacks": config.max_llm_fallbacks,
        "report_valid_llm_run": validity["report_valid_llm_run"],
        "llm_fallback_observed": validity["total_fallback_count"],
        "use_advanced_resources": config.use_advanced_resources,
        "advanced_resource_preset": [
            {"id": resource_id, "capacity": capacity, "enabled": True}
            for resource_id, capacity in ADVANCED_RESOURCE_PRESET
        ]
        if config.use_advanced_resources
        else [],
        "quick_mode": config.quick_mode,
    }


def build_environment_snapshot(config: FinalValidationConfig, provider_validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "backend_root": str(REPO_ROOT / "backend"),
        "repo_root": str(REPO_ROOT),
        "running_inside_docker": running_inside_docker(),
        "provider_validation": provider_validation,
        "environment": {
            "LLM_PROVIDER": config.llm_provider,
            "LLM_FALLBACK_ORDER": ",".join(config.llm_fallback_order),
            "LLM_FALLBACK_TO_MOCK": config.llm_fallback_to_mock,
            "LLM_CACHE_PATH": config.cache_path,
            "OLLAMA_BASE_URL": config.ollama_base_url,
            "OLLAMA_MODEL": config.ollama_model,
            "OLLAMA_TIMEOUT_SECONDS": config.ollama_timeout_seconds,
        },
    }


def build_output_readme(config: FinalValidationConfig, *, cache_reused: bool, validity: dict[str, Any]) -> str:
    lines = [
        "# Final Experimental Validation",
        "",
        "This folder contains report-ready outputs generated by `backend/scripts/run_final_experiments.py`.",
        "",
        "## Run Configuration",
        "",
        f"- LLM provider: `{config.llm_provider}`",
        f"- Fallback order: `{','.join(config.llm_fallback_order)}`",
        f"- Data source: `{config.data_source}`",
        f"- Algorithms: `{', '.join(config.algorithms)}`",
        f"- Scenarios: `{', '.join(config.scenarios)}`",
        f"- Replications: `{config.replications}`",
        f"- Duration minutes: `{config.duration_minutes}`",
        f"- Advanced resources: `{config.use_advanced_resources}`",
        f"- Cache path: `{config.cache_path}`",
        f"- Existing cache reused: `{cache_reused}`",
        f"- Report-valid LLM run: `{validity['report_valid_llm_run']}`",
        f"- Total LLM fallbacks observed: `{validity['total_fallback_count']}`",
        "",
    ]
    if validity["warning"]:
        lines.extend(
            [
                "## Warning",
                "",
                validity["warning"],
                "",
            ]
        )
    lines.extend(
        [
        "## Files",
        "",
        "- `protocol.json`: reproducibility protocol and selected defaults",
        "- `environment.json`: runtime metadata and sanitized environment summary",
        "- `final_results.json`: per-scenario aggregated experiment outputs",
        "- `final_analysis.json`: per-scenario rankings plus cross-scenario summary",
        "- `final_summary.csv`: scenario/algorithm metric summary table",
        "- `final_metric_rankings.csv`: per-metric rankings for report tables",
        "- `final_algorithm_rankings.csv`: balanced and category ranking tables",
        "- `llm_usage_summary.json`: provider usage, fallback, and cache summary",
        "",
        "These files exclude API keys and other secrets.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_final_validation_outputs(
    config: FinalValidationConfig,
    *,
    provider_validation: dict[str, Any],
    cache_reused: bool,
    results_by_scenario: dict[str, Any],
    analyses_by_scenario: dict[str, Any],
    overall_algorithm_summary: list[dict[str, Any]],
) -> dict[str, str]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    llm_usage_summary = build_llm_usage_summary(results_by_scenario)
    validity = evaluate_report_validity(config, llm_usage_summary)
    protocol = build_protocol(config, cache_reused=cache_reused, validity=validity)
    environment = build_environment_snapshot(config, provider_validation)
    final_results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": protocol,
        "report_validity": validity,
        "results_by_scenario": results_by_scenario,
    }
    final_analysis = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_validity": validity,
        "analyses_by_scenario": analyses_by_scenario,
        "overall_algorithm_summary": overall_algorithm_summary,
    }

    summary_rows = build_summary_rows(results_by_scenario)
    metric_ranking_rows = build_metric_ranking_rows(analyses_by_scenario)
    algorithm_ranking_rows = build_algorithm_ranking_rows(analyses_by_scenario)

    outputs = {
        "protocol.json": json.dumps(protocol, indent=2, sort_keys=True),
        "environment.json": json.dumps(environment, indent=2, sort_keys=True),
        "final_results.json": json.dumps(final_results, indent=2, sort_keys=True),
        "final_analysis.json": json.dumps(final_analysis, indent=2, sort_keys=True),
        "final_summary.csv": rows_to_csv(summary_rows, FINAL_SUMMARY_FIELDS),
        "final_metric_rankings.csv": rows_to_csv(metric_ranking_rows, FINAL_METRIC_RANKING_FIELDS),
        "final_algorithm_rankings.csv": rows_to_csv(algorithm_ranking_rows, FINAL_ALGORITHM_RANKING_FIELDS),
        "llm_usage_summary.json": json.dumps(llm_usage_summary, indent=2, sort_keys=True),
        "README.md": build_output_readme(config, cache_reused=cache_reused, validity=validity),
    }
    for filename, content in outputs.items():
        (config.output_dir / filename).write_text(content, encoding="utf-8")
    return {filename: str(config.output_dir / filename) for filename in outputs}
