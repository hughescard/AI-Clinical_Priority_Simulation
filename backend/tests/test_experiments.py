import pytest

from app.evaluation.aggregation import aggregate_runs_by_algorithm, summarize_metric_values
from app.evaluation.experiments import ExperimentComparisonRequest, run_experiment_comparison


def test_aggregation_computes_mean_std_min_max_correctly() -> None:
    summary = summarize_metric_values([10, 20, 30])
    assert summary == {"mean": 20.0, "std": 8.165, "min": 10.0, "max": 30.0}


def test_comparison_runs_all_requested_algorithms() -> None:
    result = run_experiment_comparison(
        ExperimentComparisonRequest(
            algorithms=["fifo", "greedy", "simulated_annealing"],
            scenario="normal",
            seed_start=42,
            replications=2,
            duration_minutes=120,
        )
    )
    assert result["algorithms"] == ["fifo", "greedy", "simulated_annealing"]
    assert set(result["results"]) == {"fifo", "greedy", "simulated_annealing"}


def test_number_of_runs_equals_algorithms_times_replications() -> None:
    result = run_experiment_comparison(
        ExperimentComparisonRequest(
            algorithms=["fifo", "greedy"],
            scenario="normal",
            seed_start=42,
            replications=3,
            duration_minutes=120,
        )
    )
    assert len(result["runs"]) == 6


def test_invalid_algorithm_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported algorithms: badalgo"):
        run_experiment_comparison(
            ExperimentComparisonRequest(
                algorithms=["fifo", "badalgo"],
                scenario="normal",
                seed_start=42,
                replications=1,
                duration_minutes=120,
            )
        )


def test_aggregate_runs_by_algorithm_structure() -> None:
    aggregated = aggregate_runs_by_algorithm(
        [
            {"algorithm": "fifo", "metrics": {"treated_patients": 3, "untreated_patients": 1, "number_of_initial_assessments": 4, "services_started_from_arrival": 2, "services_started_from_service_end": 1, "services_started_from_deterioration": 0, "services_started_from_doctor_round": 0, "average_time_to_initial_assessment": 0, "average_time_to_service_start": 10, "patients_deteriorated_while_waiting": 1, "critical_patients_waited": 1, "critical_patients_started_immediately": 0, "average_waiting_time": 10, "max_waiting_time": 20, "critical_late_patients": 1, "total_clinical_impact": 100, "average_resource_utilization": 0.2, "total_doctor_round_time": 5, "number_of_doctor_rounds": 4, "average_doctor_round_duration": 1.25, "total_planning_overhead_time": 0.4}},
            {"algorithm": "fifo", "metrics": {"treated_patients": 5, "untreated_patients": 0, "number_of_initial_assessments": 5, "services_started_from_arrival": 3, "services_started_from_service_end": 2, "services_started_from_deterioration": 0, "services_started_from_doctor_round": 0, "average_time_to_initial_assessment": 0, "average_time_to_service_start": 14, "patients_deteriorated_while_waiting": 0, "critical_patients_waited": 0, "critical_patients_started_immediately": 1, "average_waiting_time": 14, "max_waiting_time": 24, "critical_late_patients": 0, "total_clinical_impact": 80, "average_resource_utilization": 0.4, "total_doctor_round_time": 6, "number_of_doctor_rounds": 5, "average_doctor_round_duration": 1.2, "total_planning_overhead_time": 0.5}},
        ]
    )
    assert set(aggregated["fifo"]) == {
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
    }
