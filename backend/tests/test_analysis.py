from __future__ import annotations

from app.evaluation.analysis import analyze_against_baseline


def build_experiment_result() -> dict:
    return {
        "algorithms": ["fifo", "greedy", "cpsat"],
        "results": {
            "fifo": {
                "treated_patients": {"mean": 10.0, "std": 1.0, "min": 9.0, "max": 11.0},
                "untreated_patients": {"mean": 5.0, "std": 0.5, "min": 4.0, "max": 6.0},
                "average_waiting_time": {"mean": 20.0, "std": 1.0, "min": 18.0, "max": 22.0},
                "critical_late_patients": {"mean": 4.0, "std": 0.5, "min": 3.0, "max": 5.0},
                "total_clinical_impact": {"mean": 100.0, "std": 5.0, "min": 95.0, "max": 105.0},
                "average_resource_utilization": {"mean": 0.5, "std": 0.05, "min": 0.45, "max": 0.55},
                "average_time_to_service_start": {"mean": 18.0, "std": 1.0, "min": 17.0, "max": 19.0},
                "patients_deteriorated_while_waiting": {"mean": 6.0, "std": 0.5, "min": 5.0, "max": 7.0},
                "critical_patients_waited": {"mean": 5.0, "std": 0.5, "min": 4.0, "max": 6.0},
                "total_planning_overhead_time": {"mean": 1.0, "std": 0.1, "min": 0.9, "max": 1.1},
                "number_of_doctor_rounds": {"mean": 8.0, "std": 1.0, "min": 7.0, "max": 9.0},
                "services_started_from_arrival": {"mean": 3.0, "std": 0.5, "min": 2.0, "max": 4.0},
            },
            "greedy": {
                "treated_patients": {"mean": 12.0, "std": 1.0, "min": 11.0, "max": 13.0},
                "untreated_patients": {"mean": 4.0, "std": 0.5, "min": 3.0, "max": 5.0},
                "average_waiting_time": {"mean": 15.0, "std": 1.0, "min": 14.0, "max": 16.0},
                "critical_late_patients": {"mean": 2.0, "std": 0.5, "min": 1.0, "max": 3.0},
                "total_clinical_impact": {"mean": 70.0, "std": 5.0, "min": 65.0, "max": 75.0},
                "average_resource_utilization": {"mean": 0.6, "std": 0.05, "min": 0.55, "max": 0.65},
                "average_time_to_service_start": {"mean": 12.0, "std": 1.0, "min": 11.0, "max": 13.0},
                "patients_deteriorated_while_waiting": {"mean": 4.0, "std": 0.5, "min": 3.0, "max": 5.0},
                "critical_patients_waited": {"mean": 3.0, "std": 0.5, "min": 2.0, "max": 4.0},
                "total_planning_overhead_time": {"mean": 1.5, "std": 0.1, "min": 1.4, "max": 1.6},
                "number_of_doctor_rounds": {"mean": 9.0, "std": 1.0, "min": 8.0, "max": 10.0},
                "services_started_from_arrival": {"mean": 5.0, "std": 0.5, "min": 4.0, "max": 6.0},
            },
            "cpsat": {
                "treated_patients": {"mean": 11.0, "std": 1.0, "min": 10.0, "max": 12.0},
                "untreated_patients": {"mean": 6.0, "std": 0.5, "min": 5.0, "max": 7.0},
                "average_waiting_time": {"mean": 20.0, "std": 1.0, "min": 19.0, "max": 21.0},
                "critical_late_patients": {"mean": 4.0, "std": 0.5, "min": 3.0, "max": 5.0},
                "total_clinical_impact": {"mean": 110.0, "std": 5.0, "min": 105.0, "max": 115.0},
                "average_resource_utilization": {"mean": 0.4, "std": 0.05, "min": 0.35, "max": 0.45},
                "average_time_to_service_start": {"mean": 18.0, "std": 1.0, "min": 17.0, "max": 19.0},
                "patients_deteriorated_while_waiting": {"mean": 7.0, "std": 0.5, "min": 6.0, "max": 8.0},
                "critical_patients_waited": {"mean": 6.0, "std": 0.5, "min": 5.0, "max": 7.0},
                "total_planning_overhead_time": {"mean": 2.0, "std": 0.1, "min": 1.9, "max": 2.1},
                "number_of_doctor_rounds": {"mean": 7.0, "std": 1.0, "min": 6.0, "max": 8.0},
                "services_started_from_arrival": {"mean": 3.0, "std": 0.5, "min": 2.0, "max": 4.0},
            },
        },
    }


def build_practical_tie_result() -> dict:
    return {
        "algorithms": ["fifo", "greedy", "cpsat"],
        "results": {
            "fifo": {"average_waiting_time": {"mean": 10.21, "std": 0.1, "min": 10.0, "max": 10.4}},
            "greedy": {"average_waiting_time": {"mean": 10.34, "std": 0.1, "min": 10.1, "max": 10.5}},
            "cpsat": {"average_waiting_time": {"mean": 12.5, "std": 0.1, "min": 12.3, "max": 12.7}},
        },
    }


def build_practical_tie_higher_result() -> dict:
    return {
        "algorithms": ["fifo", "greedy", "cpsat"],
        "results": {
            "fifo": {"treated_patients": {"mean": 100.0, "std": 1.0, "min": 99.0, "max": 101.0}},
            "greedy": {"treated_patients": {"mean": 101.9, "std": 1.0, "min": 101.0, "max": 103.0}},
            "cpsat": {"treated_patients": {"mean": 95.0, "std": 1.0, "min": 94.0, "max": 96.0}},
        },
    }


def test_overall_ranking_remains_available_for_backward_compatibility() -> None:
    analysis = analyze_against_baseline(build_experiment_result())
    assert analysis["overall_ranking"] == analysis["balanced_overall_ranking"]
    assert analysis["overall_ranking"][0]["algorithm"] == "greedy"


def test_practical_tie_logic_gives_same_rank_for_lower_is_better_means_within_tolerance() -> None:
    analysis = analyze_against_baseline(build_practical_tie_result())
    row = analysis["per_metric_rankings"][0]
    assert [entry["algorithm"] for entry in row["ranking"]] == ["fifo", "greedy", "cpsat"]
    assert [entry["rank"] for entry in row["ranking"]] == [1, 1, 2]


def test_practical_tie_logic_gives_same_rank_for_higher_is_better_means_within_tolerance() -> None:
    analysis = analyze_against_baseline(build_practical_tie_higher_result())
    row = analysis["per_metric_rankings"][0]
    assert [entry["algorithm"] for entry in row["ranking"]] == ["greedy", "fifo", "cpsat"]
    assert [entry["rank"] for entry in row["ranking"]] == [1, 1, 2]


def test_clinical_ranking_includes_only_clinical_metrics() -> None:
    analysis = analyze_against_baseline(build_experiment_result())
    assert analysis["clinical_ranking"]["included_metrics"] == [
        "critical_late_patients",
        "total_clinical_impact",
        "untreated_patients",
        "patients_deteriorated_while_waiting",
        "critical_patients_waited",
    ]


def test_operational_ranking_includes_only_operational_metrics() -> None:
    analysis = analyze_against_baseline(build_experiment_result())
    assert analysis["operational_ranking"]["included_metrics"] == [
        "average_waiting_time",
        "average_time_to_service_start",
        "treated_patients",
        "average_resource_utilization",
        "services_started_from_arrival",
    ]


def test_computational_ranking_includes_only_computational_metrics() -> None:
    analysis = analyze_against_baseline(build_experiment_result())
    assert analysis["computational_ranking"]["included_metrics"] == ["total_planning_overhead_time"]
    assert analysis["computational_ranking"]["ranking"][0]["algorithm"] == "fifo"


def test_balanced_overall_ranking_uses_category_weights() -> None:
    analysis = analyze_against_baseline(build_experiment_result())
    top_row = analysis["balanced_overall_ranking"][0]
    assert top_row["algorithm"] == "greedy"
    assert top_row["balanced_score"] == 0.95
    assert top_row["clinical_score"] == 1.0
    assert top_row["operational_score"] == 1.0
    assert round(top_row["computational_score"], 4) == 0.6667


def test_balanced_overall_ranking_tie_breaks_deterministically() -> None:
    result = {
        "algorithms": ["fifo", "greedy"],
        "results": {
            "fifo": {
                "critical_late_patients": {"mean": 5.0, "std": 0.0, "min": 5.0, "max": 5.0},
                "average_waiting_time": {"mean": 10.0, "std": 0.0, "min": 10.0, "max": 10.0},
                "total_planning_overhead_time": {"mean": 1.0, "std": 0.0, "min": 1.0, "max": 1.0},
            },
            "greedy": {
                "critical_late_patients": {"mean": 5.0, "std": 0.0, "min": 5.0, "max": 5.0},
                "average_waiting_time": {"mean": 10.0, "std": 0.0, "min": 10.0, "max": 10.0},
                "total_planning_overhead_time": {"mean": 1.0, "std": 0.0, "min": 1.0, "max": 1.0},
            },
        },
    }
    analysis = analyze_against_baseline(result)
    assert [row["algorithm"] for row in analysis["balanced_overall_ranking"]] == ["fifo", "greedy"]


def test_baseline_analysis_remains_available() -> None:
    analysis = analyze_against_baseline(build_experiment_result())
    assert analysis["baseline_analysis"]["baseline_algorithm"] == "fifo"
    assert analysis["baseline_analysis"]["available"] is True
    assert analysis["baseline_available"] is True


def test_headline_findings_are_ranking_contextual_and_deterministic() -> None:
    analysis = analyze_against_baseline(build_experiment_result())
    assert analysis["headline_findings"][:4] == [
        "The balanced ranking favors the algorithm with the strongest combined clinical, operational, and computational profile.",
        "GREEDY ranked first in the balanced overall ranking.",
        "GREEDY ranked first in the clinical ranking, driven by Critical Late Patients.",
        "FIFO ranked first in computational cost because it had the lowest planning overhead.",
    ]


def test_analysis_handles_missing_fifo_without_failing() -> None:
    result = build_experiment_result()
    result["algorithms"] = ["greedy", "cpsat"]
    result["results"].pop("fifo")
    analysis = analyze_against_baseline(result)
    assert analysis["baseline_analysis"]["available"] is False
    assert analysis["baseline_analysis"]["comparisons_vs_baseline"] == []


def test_baseline_comparison_improvement_is_preserved() -> None:
    analysis = analyze_against_baseline(build_experiment_result())
    row = next(
        item
        for item in analysis["comparisons_vs_baseline"]
        if item["algorithm"] == "greedy" and item["metric_name"] == "average_waiting_time"
    )
    assert row["improvement_percent"] == 25.0
    assert row["status"] == "improved"


def test_zero_baseline_does_not_crash() -> None:
    result = build_experiment_result()
    result["results"]["fifo"]["treated_patients"]["mean"] = 0.0
    analysis = analyze_against_baseline(result)
    row = next(
        item
        for item in analysis["comparisons_vs_baseline"]
        if item["algorithm"] == "greedy" and item["metric_name"] == "treated_patients"
    )
    assert row["improvement_percent"] is None


def test_analysis_includes_simulated_annealing_when_present() -> None:
    result = build_experiment_result()
    result["algorithms"].append("simulated_annealing")
    result["results"]["simulated_annealing"] = {
        "treated_patients": {"mean": 11.5, "std": 1.0, "min": 10.0, "max": 13.0},
        "untreated_patients": {"mean": 4.5, "std": 0.5, "min": 4.0, "max": 5.0},
        "average_waiting_time": {"mean": 16.0, "std": 1.0, "min": 15.0, "max": 17.0},
        "critical_late_patients": {"mean": 3.0, "std": 0.5, "min": 2.0, "max": 4.0},
        "total_clinical_impact": {"mean": 85.0, "std": 5.0, "min": 80.0, "max": 90.0},
        "average_resource_utilization": {"mean": 0.58, "std": 0.05, "min": 0.53, "max": 0.63},
        "average_time_to_service_start": {"mean": 13.0, "std": 1.0, "min": 12.0, "max": 14.0},
        "patients_deteriorated_while_waiting": {"mean": 4.5, "std": 0.5, "min": 4.0, "max": 5.0},
        "critical_patients_waited": {"mean": 3.5, "std": 0.5, "min": 3.0, "max": 4.0},
        "total_planning_overhead_time": {"mean": 1.7, "std": 0.1, "min": 1.6, "max": 1.8},
        "number_of_doctor_rounds": {"mean": 8.0, "std": 1.0, "min": 7.0, "max": 9.0},
        "services_started_from_arrival": {"mean": 4.0, "std": 0.5, "min": 3.0, "max": 5.0},
    }

    analysis = analyze_against_baseline(result)

    ranked_algorithms = [row["algorithm"] for row in analysis["balanced_overall_ranking"]]
    assert "simulated_annealing" in ranked_algorithms
