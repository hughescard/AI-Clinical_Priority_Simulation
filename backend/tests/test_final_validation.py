from __future__ import annotations

import importlib.util
from pathlib import Path

from app.evaluation.final_validation import (
    QUICK_MODE_ALGORITHMS,
    QUICK_MODE_DURATION_MINUTES,
    QUICK_MODE_REPLICATIONS,
    QUICK_MODE_SCENARIOS,
    build_advanced_resource_config,
    build_llm_usage_summary,
    build_output_readme,
    build_protocol,
    build_summary_rows,
    evaluate_report_validity,
    resolve_run_configuration,
    validate_ollama_configuration,
    write_final_validation_outputs,
)


class FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeHTTPClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def get(self, url: str, timeout: float | None = None):
        self.calls.append(url)
        return FakeHTTPResponse(self.payload)


def test_quick_mode_uses_expected_defaults(tmp_path: Path) -> None:
    config = resolve_run_configuration(
        quick_mode=True,
        algorithms=None,
        scenarios=None,
        replications=None,
        duration_minutes=None,
        data_source="synthetic",
        seed_start=42,
        llm_provider=None,
        llm_fallback_order=None,
        llm_fallback_to_mock=True,
        ollama_base_url=None,
        ollama_model=None,
        ollama_timeout_seconds=None,
        cache_path=None,
        use_advanced_resources=True,
        output_dir=tmp_path / "final",
        fail_on_llm_fallback=False,
        max_llm_fallbacks=None,
    )

    assert config.llm_provider == "ollama"
    assert config.algorithms == QUICK_MODE_ALGORITHMS
    assert config.scenarios == QUICK_MODE_SCENARIOS
    assert config.replications == QUICK_MODE_REPLICATIONS
    assert config.duration_minutes == QUICK_MODE_DURATION_MINUTES


def test_fail_on_llm_fallback_forces_zero_max_fallbacks(tmp_path: Path) -> None:
    config = resolve_run_configuration(
        quick_mode=False,
        algorithms=["fifo"],
        scenarios=["normal"],
        replications=1,
        duration_minutes=120,
        data_source="synthetic",
        seed_start=42,
        llm_provider="ollama",
        llm_fallback_order=["ollama", "mock"],
        llm_fallback_to_mock=True,
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.2:3b",
        ollama_timeout_seconds=30,
        cache_path=str(tmp_path / "cache.json"),
        use_advanced_resources=False,
        output_dir=tmp_path / "out",
        fail_on_llm_fallback=True,
        max_llm_fallbacks=None,
    )

    assert config.max_llm_fallbacks == 0


def test_advanced_resource_config_contains_expected_catalog() -> None:
    advanced_config = build_advanced_resource_config()
    catalog = {resource.id: resource.capacity for resource in advanced_config.resources}

    assert catalog["doctor"] == 2
    assert catalog["ct_scanner"] == 1
    assert catalog["specialist"] == 1
    assert len(catalog) == 12


def test_validate_ollama_configuration_checks_url_model_and_reachability() -> None:
    client = FakeHTTPClient({"models": [{"name": "llama3.2:3b"}]})

    validation = validate_ollama_configuration(
        base_url="http://localhost:11434",
        model="llama3.2:3b",
        timeout_seconds=30,
        client=client,
    )

    assert validation["provider"] == "ollama"
    assert validation["reachable"] is True
    assert validation["available_models"] == ["llama3.2:3b"]
    assert client.calls == ["http://localhost:11434/api/tags"]


def test_build_llm_usage_summary_aggregates_attempts_and_cache_stats() -> None:
    summary = build_llm_usage_summary(
        {
            "high_demand": {
                "runs": [
                    {
                        "llm_provider_requested": "ollama",
                        "llm_provider_used": "ollama",
                        "llm_fallback_count": 0,
                        "llm_cache_hits": 3,
                        "llm_cache_misses": 1,
                        "llm_provider_attempts": {"ollama": {"successes": 1, "failures": 0}},
                        "llm_provider_retries": {"ollama": 1},
                    },
                    {
                        "llm_provider_requested": "ollama",
                        "llm_provider_used": "mock",
                        "llm_fallback_count": 1,
                        "llm_cache_hits": 0,
                        "llm_cache_misses": 2,
                        "llm_provider_attempts": {
                            "ollama": {"successes": 0, "failures": 1},
                            "mock": {"successes": 1, "failures": 0},
                        },
                        "llm_provider_retries": {"ollama": 1, "mock": 0},
                    },
                ]
            }
        }
    )

    assert summary["total_runs"] == 2
    assert summary["provider_requested_counts"] == {"ollama": 2}
    assert summary["provider_used_counts"] == {"ollama": 1, "mock": 1}
    assert summary["total_fallback_count"] == 1
    assert summary["total_cache_hits"] == 3
    assert summary["total_cache_misses"] == 3
    assert summary["provider_attempt_totals"]["ollama"] == {"successes": 1, "failures": 1}
    assert summary["provider_retry_totals"]["ollama"] == 2


def test_build_summary_rows_spans_scenarios_algorithms_and_metrics() -> None:
    rows = build_summary_rows(
        {
            "normal": {
                "replications": 2,
                "results": {
                    "fifo": {
                        "treated_patients": {"mean": 10, "std": 1, "min": 9, "max": 11},
                        **{
                            metric: {"mean": 0, "std": 0, "min": 0, "max": 0}
                            for metric in (
                                "untreated_patients",
                                "number_of_initial_assessments",
                                "services_started_from_arrival",
                                "services_started_from_service_end",
                                "services_started_from_deterioration",
                                "services_started_from_doctor_round",
                                "average_time_to_initial_assessment",
                                "average_time_to_service_start",
                                "patients_deteriorated_while_waiting",
                                "critical_patients_waited",
                                "critical_patients_started_immediately",
                                "average_waiting_time",
                                "max_waiting_time",
                                "critical_late_patients",
                                "total_clinical_impact",
                                "average_resource_utilization",
                                "total_doctor_round_time",
                                "number_of_doctor_rounds",
                                "average_doctor_round_duration",
                                "total_planning_overhead_time",
                            )
                        },
                    }
                },
            }
        }
    )

    treated_row = next(row for row in rows if row["metric_name"] == "treated_patients")
    assert treated_row["scenario"] == "normal"
    assert treated_row["algorithm"] == "fifo"
    assert treated_row["replications"] == 2


def test_report_validity_marks_fallback_runs_invalid(tmp_path: Path) -> None:
    config = resolve_run_configuration(
        quick_mode=False,
        algorithms=["fifo"],
        scenarios=["normal"],
        replications=1,
        duration_minutes=120,
        data_source="synthetic",
        seed_start=42,
        llm_provider="ollama",
        llm_fallback_order=["ollama", "mock"],
        llm_fallback_to_mock=True,
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.2:3b",
        ollama_timeout_seconds=30,
        cache_path=str(tmp_path / "cache.json"),
        use_advanced_resources=False,
        output_dir=tmp_path / "out",
        fail_on_llm_fallback=False,
        max_llm_fallbacks=100,
    )
    validity = evaluate_report_validity(config, {"total_fallback_count": 1})

    assert validity["report_valid_llm_run"] is False
    assert validity["within_allowed_fallback_limit"] is True
    assert "not suitable for final report claims" in validity["warning"]


def test_protocol_and_readme_mark_report_validity(tmp_path: Path) -> None:
    config = resolve_run_configuration(
        quick_mode=False,
        algorithms=["fifo"],
        scenarios=["normal"],
        replications=1,
        duration_minutes=120,
        data_source="synthetic",
        seed_start=42,
        llm_provider="ollama",
        llm_fallback_order=["ollama", "mock"],
        llm_fallback_to_mock=True,
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.2:3b",
        ollama_timeout_seconds=30,
        cache_path=str(tmp_path / "cache.json"),
        use_advanced_resources=False,
        output_dir=tmp_path / "out",
        fail_on_llm_fallback=False,
        max_llm_fallbacks=100,
    )
    validity = evaluate_report_validity(config, {"total_fallback_count": 1})
    protocol = build_protocol(config, cache_reused=False, validity=validity)
    readme = build_output_readme(config, cache_reused=False, validity=validity)

    assert protocol["report_valid_llm_run"] is False
    assert protocol["llm_fallback_observed"] == 1
    assert "Report-valid LLM run: `False`" in readme
    assert "## Warning" in readme


def test_write_outputs_marks_report_validity_false_when_fallback_occurs(tmp_path: Path) -> None:
    config = resolve_run_configuration(
        quick_mode=False,
        algorithms=["fifo"],
        scenarios=["normal"],
        replications=1,
        duration_minutes=120,
        data_source="synthetic",
        seed_start=42,
        llm_provider="ollama",
        llm_fallback_order=["ollama", "mock"],
        llm_fallback_to_mock=True,
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.2:3b",
        ollama_timeout_seconds=30,
        cache_path=str(tmp_path / "cache.json"),
        use_advanced_resources=False,
        output_dir=tmp_path / "out",
        fail_on_llm_fallback=False,
        max_llm_fallbacks=100,
    )
    write_final_validation_outputs(
        config,
        provider_validation={"provider": "ollama", "reachable": True},
        cache_reused=False,
        results_by_scenario={
            "normal": {
                "replications": 1,
                "runs": [
                    {
                        "llm_provider_requested": "ollama",
                        "llm_provider_used": "mock",
                        "llm_fallback_count": 1,
                        "llm_cache_hits": 0,
                        "llm_cache_misses": 1,
                        "llm_provider_attempts": {"ollama": {"successes": 0, "failures": 1}, "mock": {"successes": 1, "failures": 0}},
                        "llm_provider_retries": {"ollama": 1, "mock": 0},
                    }
                ],
                "results": {
                    "fifo": {
                        metric: {"mean": 0, "std": 0, "min": 0, "max": 0}
                        for metric in (
                            "treated_patients",
                            "untreated_patients",
                            "number_of_initial_assessments",
                            "services_started_from_arrival",
                            "services_started_from_service_end",
                            "services_started_from_deterioration",
                            "services_started_from_doctor_round",
                            "average_time_to_initial_assessment",
                            "average_time_to_service_start",
                            "patients_deteriorated_while_waiting",
                            "critical_patients_waited",
                            "critical_patients_started_immediately",
                            "average_waiting_time",
                            "max_waiting_time",
                            "critical_late_patients",
                            "total_clinical_impact",
                            "average_resource_utilization",
                            "total_doctor_round_time",
                            "number_of_doctor_rounds",
                            "average_doctor_round_duration",
                            "total_planning_overhead_time",
                        )
                    }
                },
            }
        },
        analyses_by_scenario={"normal": {"balanced_overall_ranking": [], "per_metric_rankings": []}},
        overall_algorithm_summary=[],
    )

    protocol_text = (config.output_dir / "protocol.json").read_text(encoding="utf-8")
    readme_text = (config.output_dir / "README.md").read_text(encoding="utf-8")
    assert '"report_valid_llm_run": false' in protocol_text
    assert "Results completed, but they are not suitable for final report claims" in readme_text


def test_fail_on_llm_fallback_runner_returns_non_zero(tmp_path: Path, monkeypatch) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_final_experiments.py"
    spec = importlib.util.spec_from_file_location("run_final_experiments", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, "validate_provider_configuration", lambda config: {"provider": "ollama", "reachable": True})
    monkeypatch.setattr(
        module,
        "run_final_validation",
        lambda config: {
            "results_by_scenario": {
                "normal": {
                    "runs": [{"llm_fallback_count": 1, "llm_provider_requested": "ollama", "llm_provider_used": "mock"}],
                    "results": {},
                    "replications": 1,
                }
            },
            "analyses_by_scenario": {},
            "overall_algorithm_summary": [],
        },
    )
    monkeypatch.setattr(module, "write_final_validation_outputs", lambda *args, **kwargs: {"protocol.json": "x"})
    monkeypatch.setattr(module.sys, "argv", ["run_final_experiments.py", "--quick", "--fail-on-llm-fallback"])

    assert module.main() == 1


def test_fail_on_llm_fallback_runner_succeeds_when_no_fallback(tmp_path: Path, monkeypatch) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_final_experiments.py"
    spec = importlib.util.spec_from_file_location("run_final_experiments", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, "validate_provider_configuration", lambda config: {"provider": "ollama", "reachable": True})
    monkeypatch.setattr(
        module,
        "run_final_validation",
        lambda config: {
            "results_by_scenario": {
                "normal": {
                    "runs": [{"llm_fallback_count": 0, "llm_provider_requested": "ollama", "llm_provider_used": "ollama"}],
                    "results": {},
                    "replications": 1,
                }
            },
            "analyses_by_scenario": {},
            "overall_algorithm_summary": [],
        },
    )
    monkeypatch.setattr(module, "write_final_validation_outputs", lambda *args, **kwargs: {"protocol.json": "x"})
    monkeypatch.setattr(module.sys, "argv", ["run_final_experiments.py", "--quick", "--fail-on-llm-fallback"])

    assert module.main() == 0
