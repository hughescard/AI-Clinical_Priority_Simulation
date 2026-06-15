from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.evaluation.aggregation import AGGREGATED_METRICS
from app.models.simulation import SimulationResult

if TYPE_CHECKING:
    from app.api.simulation_routes import SimulationRequest
    from app.evaluation.experiments import ExperimentComparisonRequest


SIMULATION_CSV_FIELDS = [
    "algorithm",
    "scenario",
    "data_source",
    "seed",
    "duration_minutes",
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
    "clinical_impact",
    "average_resource_utilization",
    "number_of_doctor_rounds",
    "average_doctor_round_duration",
    "total_doctor_round_time",
    "total_planning_overhead_time",
    "llm_provider_requested",
    "llm_provider_used",
]


EXPERIMENT_RUN_CSV_FIELDS = SIMULATION_CSV_FIELDS.copy()

EXPERIMENT_SUMMARY_CSV_FIELDS = [
    "algorithm",
    "metric_name",
    "mean",
    "std",
    "min",
    "max",
    "replications",
]


def generated_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def simulation_result_to_export_dict(request: SimulationRequest, result: SimulationResult) -> dict[str, Any]:
    return {
        "generated_at": generated_timestamp(),
        "request": request.model_dump(mode="json"),
        "reproducibility": {
            "seed": request.seed,
            "algorithm": request.algorithm,
            "scenario": request.scenario,
            "data_source": request.data_source,
            "duration_minutes": request.duration_minutes,
        },
        "result": result.model_dump(mode="json"),
    }


def simulation_result_to_csv_rows(result: SimulationResult) -> list[dict[str, Any]]:
    metrics = result.metrics
    return [
        {
            "algorithm": result.algorithm,
            "scenario": result.scenario,
            "data_source": result.data_source,
            "seed": result.seed,
            "duration_minutes": result.duration_minutes,
            "treated_patients": metrics.get("treated_patients", 0),
            "untreated_patients": metrics.get("untreated_patients", 0),
            "number_of_initial_assessments": metrics.get("number_of_initial_assessments", 0),
            "services_started_from_arrival": metrics.get("services_started_from_arrival", 0),
            "services_started_from_service_end": metrics.get("services_started_from_service_end", 0),
            "services_started_from_deterioration": metrics.get("services_started_from_deterioration", 0),
            "services_started_from_doctor_round": metrics.get("services_started_from_doctor_round", 0),
            "average_time_to_initial_assessment": metrics.get("average_time_to_initial_assessment", 0),
            "average_time_to_service_start": metrics.get("average_time_to_service_start", 0),
            "patients_deteriorated_while_waiting": metrics.get("patients_deteriorated_while_waiting", 0),
            "critical_patients_waited": metrics.get("critical_patients_waited", 0),
            "critical_patients_started_immediately": metrics.get("critical_patients_started_immediately", 0),
            "average_waiting_time": metrics.get("average_waiting_time", 0),
            "max_waiting_time": metrics.get("max_waiting_time", 0),
            "critical_late_patients": metrics.get("critical_late_patients", 0),
            "clinical_impact": metrics.get("total_clinical_impact", 0),
            "average_resource_utilization": metrics.get("average_resource_utilization", 0),
            "number_of_doctor_rounds": metrics.get("number_of_doctor_rounds", 0),
            "average_doctor_round_duration": metrics.get("average_doctor_round_duration", 0),
            "total_doctor_round_time": metrics.get("total_doctor_round_time", 0),
            "total_planning_overhead_time": metrics.get("total_planning_overhead_time", 0),
            "llm_provider_requested": result.llm_provider_requested,
            "llm_provider_used": result.llm_provider_used,
        }
    ]


def experiment_result_to_export_dict(request: ExperimentComparisonRequest, result: dict[str, Any]) -> dict[str, Any]:
    seeds_used = [run["seed"] for run in result.get("runs", [])]
    return {
        "generated_at": generated_timestamp(),
        "request": request.model_dump(mode="json"),
        "reproducibility": {
            "algorithms": list(request.algorithms),
            "scenario": request.scenario,
            "data_source": request.data_source,
            "seed_start": request.seed_start,
            "seed_range": [min(seeds_used), max(seeds_used)] if seeds_used else [request.seed_start, request.seed_start],
            "seeds_used": seeds_used,
            "replications": request.replications,
            "duration_minutes": request.duration_minutes,
        },
        "result": result,
    }


def experiment_result_to_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in result.get("runs", []):
        metrics = run.get("metrics", {})
        rows.append(
            {
                "algorithm": run.get("algorithm"),
                "scenario": result.get("scenario"),
                "data_source": result.get("data_source"),
                "seed": run.get("seed"),
                "duration_minutes": result.get("duration_minutes"),
                "treated_patients": metrics.get("treated_patients", 0),
                "untreated_patients": metrics.get("untreated_patients", 0),
                "number_of_initial_assessments": metrics.get("number_of_initial_assessments", 0),
                "services_started_from_arrival": metrics.get("services_started_from_arrival", 0),
                "services_started_from_service_end": metrics.get("services_started_from_service_end", 0),
                "services_started_from_deterioration": metrics.get("services_started_from_deterioration", 0),
                "services_started_from_doctor_round": metrics.get("services_started_from_doctor_round", 0),
                "average_time_to_initial_assessment": metrics.get("average_time_to_initial_assessment", 0),
                "average_time_to_service_start": metrics.get("average_time_to_service_start", 0),
                "patients_deteriorated_while_waiting": metrics.get("patients_deteriorated_while_waiting", 0),
                "critical_patients_waited": metrics.get("critical_patients_waited", 0),
                "critical_patients_started_immediately": metrics.get("critical_patients_started_immediately", 0),
                "average_waiting_time": metrics.get("average_waiting_time", 0),
                "max_waiting_time": metrics.get("max_waiting_time", 0),
                "critical_late_patients": metrics.get("critical_late_patients", 0),
                "clinical_impact": metrics.get("total_clinical_impact", 0),
                "average_resource_utilization": metrics.get("average_resource_utilization", 0),
                "number_of_doctor_rounds": metrics.get("number_of_doctor_rounds", 0),
                "average_doctor_round_duration": metrics.get("average_doctor_round_duration", 0),
                "total_doctor_round_time": metrics.get("total_doctor_round_time", 0),
                "total_planning_overhead_time": metrics.get("total_planning_overhead_time", 0),
                "llm_provider_requested": run.get("llm_provider_requested"),
                "llm_provider_used": run.get("llm_provider_used"),
            }
        )
    return rows


def experiment_summary_to_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    replications = int(result.get("replications", 0))
    for algorithm, metrics in result.get("results", {}).items():
        for metric_name in AGGREGATED_METRICS:
            summary = metrics.get(metric_name, {})
            rows.append(
                {
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


def rows_to_csv(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fieldnames})
    return buffer.getvalue()
