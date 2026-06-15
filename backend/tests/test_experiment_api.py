import asyncio
import json

import pytest
from pydantic import ValidationError

from app.api.experiment_routes import (
    analyze_experiments,
    compare_experiments,
    export_experiments_csv,
    export_experiments_json,
    export_experiments_summary_csv,
)
from app.evaluation.experiments import ExperimentComparisonRequest


def test_replications_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        ExperimentComparisonRequest(
            algorithms=["fifo"],
            scenario="normal",
            seed_start=42,
            replications=0,
            duration_minutes=120,
        )


def test_experiment_api_returns_expected_structure() -> None:
    payload = asyncio.run(
        compare_experiments(
            ExperimentComparisonRequest(
                algorithms=["fifo", "greedy"],
                scenario="normal",
                seed_start=42,
                replications=2,
                duration_minutes=120,
            )
        )
    )
    assert payload["scenario"] == "normal"
    assert payload["seed_start"] == 42
    assert payload["replications"] == 2
    assert payload["duration_minutes"] == 120
    assert payload["algorithms"] == ["fifo", "greedy"]
    assert set(payload["results"]) == {"fifo", "greedy"}
    assert len(payload["runs"]) == 4
    assert payload["advanced_config"] is None


def test_experiment_api_accepts_advanced_config() -> None:
    payload = asyncio.run(
        compare_experiments(
            ExperimentComparisonRequest(
                algorithms=["fifo"],
                scenario="normal",
                seed_start=42,
                replications=1,
                duration_minutes=120,
                advanced_config={
                    "resources": [
                        {"id": "doctor", "capacity": 2, "enabled": True},
                        {"id": "ct_scanner", "capacity": 1, "enabled": True},
                    ]
                },
            )
        )
    )
    assert payload["advanced_config"]["resources"][1]["id"] == "ct_scanner"


def test_experiment_api_can_run_with_mimic_sample() -> None:
    payload = asyncio.run(
        compare_experiments(
            ExperimentComparisonRequest(
                algorithms=["fifo"],
                scenario="normal",
                seed_start=42,
                data_source="mimic_iv_ed_sample",
                replications=2,
                duration_minutes=120,
            )
        )
    )
    assert payload["data_source"] == "mimic_iv_ed_sample"
    assert len(payload["runs"]) == 2


def test_experiment_api_accepts_cpsat() -> None:
    payload = asyncio.run(
        compare_experiments(
            ExperimentComparisonRequest(
                algorithms=["cpsat"],
                scenario="normal",
                seed_start=42,
                data_source="synthetic",
                replications=1,
                duration_minutes=120,
            )
        )
    )
    assert payload["algorithms"] == ["cpsat"]
    assert payload["runs"][0]["algorithm"] == "cpsat"


def test_experiment_api_accepts_simulated_annealing() -> None:
    payload = asyncio.run(
        compare_experiments(
            ExperimentComparisonRequest(
                algorithms=["simulated_annealing"],
                scenario="normal",
                seed_start=42,
                data_source="synthetic",
                replications=1,
                duration_minutes=120,
            )
        )
    )
    assert payload["algorithms"] == ["simulated_annealing"]
    assert payload["runs"][0]["algorithm"] == "simulated_annealing"


def test_experiment_json_export_returns_valid_json() -> None:
    response = asyncio.run(
        export_experiments_json(
            ExperimentComparisonRequest(
                algorithms=["fifo", "greedy"],
                scenario="normal",
                seed_start=42,
                replications=2,
                duration_minutes=120,
            )
        )
    )
    payload = json.loads(response.body.decode("utf-8"))
    assert response.status_code == 200
    assert payload["request"]["algorithms"] == ["fifo", "greedy"]
    assert payload["result"]["replications"] == 2
    assert "generated_at" in payload


def test_analysis_endpoint_returns_expected_structure() -> None:
    payload = asyncio.run(
        analyze_experiments(
            ExperimentComparisonRequest(
                algorithms=["fifo", "greedy"],
                scenario="normal",
                seed_start=42,
                replications=2,
                duration_minutes=120,
            )
        )
    )
    assert "comparison" in payload
    assert "analysis" in payload
    assert "clinical_ranking" in payload["analysis"]
    assert "operational_ranking" in payload["analysis"]
    assert "computational_ranking" in payload["analysis"]
    assert "balanced_overall_ranking" in payload["analysis"]
    assert "overall_ranking" in payload["analysis"]
    assert "per_metric_rankings" in payload["analysis"]
    assert payload["analysis"]["baseline_analysis"]["baseline_algorithm"] == "fifo"
    assert isinstance(payload["analysis"]["headline_findings"], list)


def test_experiment_csv_export_returns_expected_columns() -> None:
    response = asyncio.run(
        export_experiments_csv(
            ExperimentComparisonRequest(
                algorithms=["fifo"],
                scenario="normal",
                seed_start=42,
                replications=2,
                duration_minutes=120,
            )
        )
    )
    header = response.body.decode("utf-8").splitlines()[0]
    assert response.status_code == 200
    assert "algorithm,scenario,data_source,seed,duration_minutes" in header
    assert "llm_provider_requested" in header
    assert "llm_provider_used" in header
    assert "number_of_initial_assessments" in header
    assert "services_started_from_arrival" in header
    assert "patients_deteriorated_while_waiting" in header


def test_experiment_summary_csv_export_includes_rows() -> None:
    response = asyncio.run(
        export_experiments_summary_csv(
            ExperimentComparisonRequest(
                algorithms=["fifo"],
                scenario="normal",
                seed_start=42,
                replications=2,
                duration_minutes=120,
            )
        )
    )
    lines = response.body.decode("utf-8").splitlines()
    assert response.status_code == 200
    assert lines[0] == "algorithm,metric_name,mean,std,min,max,replications"
    assert len(lines) > 1
    assert any("services_started_from_arrival" in line for line in lines[1:])
