from __future__ import annotations

from statistics import mean, pstdev


AGGREGATED_METRICS = (
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


def summarize_metric_values(values: list[float | int]) -> dict[str, float]:
    normalized = [float(value) for value in values]
    return {
        "mean": round(mean(normalized), 4) if normalized else 0.0,
        "std": round(pstdev(normalized), 4) if len(normalized) > 1 else 0.0,
        "min": round(min(normalized), 4) if normalized else 0.0,
        "max": round(max(normalized), 4) if normalized else 0.0,
    }


def aggregate_runs_by_algorithm(runs: list[dict]) -> dict[str, dict[str, dict[str, float]]]:
    grouped: dict[str, list[dict]] = {}
    for run in runs:
        grouped.setdefault(run["algorithm"], []).append(run["metrics"])
    aggregated: dict[str, dict[str, dict[str, float]]] = {}
    for algorithm, metrics_list in grouped.items():
        aggregated[algorithm] = {
            metric_name: summarize_metric_values([metrics[metric_name] for metrics in metrics_list])
            for metric_name in AGGREGATED_METRICS
        }
    return aggregated
