from __future__ import annotations

from typing import Any


LOWER_IS_BETTER_METRICS = {
    "untreated_patients",
    "average_waiting_time",
    "max_waiting_time",
    "critical_late_patients",
    "total_clinical_impact",
    "total_planning_overhead_time",
    "average_time_to_service_start",
    "patients_deteriorated_while_waiting",
    "critical_patients_waited",
}

HIGHER_IS_BETTER_METRICS = {
    "treated_patients",
    "average_resource_utilization",
    "critical_patients_started_immediately",
    "services_started_from_arrival",
    "services_started_from_service_end",
}

NEUTRAL_METRICS = {
    "number_of_doctor_rounds",
    "average_doctor_round_duration",
    "total_doctor_round_time",
    "number_of_initial_assessments",
    "services_started_from_deterioration",
    "services_started_from_doctor_round",
    "average_time_to_initial_assessment",
}

CLINICAL_METRICS = [
    "critical_late_patients",
    "total_clinical_impact",
    "untreated_patients",
    "patients_deteriorated_while_waiting",
    "critical_patients_waited",
    "critical_patients_started_immediately",
]

OPERATIONAL_METRICS = [
    "average_waiting_time",
    "max_waiting_time",
    "average_time_to_service_start",
    "treated_patients",
    "average_resource_utilization",
    "services_started_from_arrival",
    "services_started_from_service_end",
]

COMPUTATIONAL_METRICS = [
    "total_planning_overhead_time",
]

CATEGORY_WEIGHTS = {
    "clinical": 0.50,
    "operational": 0.35,
    "computational": 0.15,
}

METRIC_DISPLAY_NAMES = {
    "treated_patients": "Treated Patients",
    "untreated_patients": "Untreated Patients",
    "average_waiting_time": "Average Waiting Time",
    "max_waiting_time": "Maximum Waiting Time",
    "critical_late_patients": "Critical Late Patients",
    "total_clinical_impact": "Total Clinical Impact",
    "average_resource_utilization": "Average Resource Utilization",
    "total_planning_overhead_time": "Total Planning Overhead Time",
    "average_time_to_service_start": "Average Time To Service Start",
    "patients_deteriorated_while_waiting": "Patients Deteriorated While Waiting",
    "critical_patients_waited": "Critical Patients Waited",
    "critical_patients_started_immediately": "Critical Patients Started Immediately",
    "services_started_from_arrival": "Services Started From Arrival",
    "services_started_from_service_end": "Services Started From Service End",
    "number_of_doctor_rounds": "Number Of Doctor Rounds",
    "average_doctor_round_duration": "Average Doctor Round Duration",
    "total_doctor_round_time": "Total Doctor Round Time",
    "number_of_initial_assessments": "Number Of Initial Assessments",
    "services_started_from_deterioration": "Services Started From Deterioration",
    "services_started_from_doctor_round": "Services Started From Doctor Round",
    "average_time_to_initial_assessment": "Average Time To Initial Assessment",
}

HEADLINE_PRIORITY = [
    "critical_late_patients",
    "total_clinical_impact",
    "average_waiting_time",
    "untreated_patients",
    "average_time_to_service_start",
    "treated_patients",
    "average_resource_utilization",
    "total_planning_overhead_time",
]

EPSILON = 1e-9
DEFAULT_RELATIVE_TOLERANCE = 0.02
HEADLINE_THRESHOLD_PERCENT = 1.0


def metric_direction(metric_name: str) -> str:
    if metric_name in LOWER_IS_BETTER_METRICS:
        return "lower_is_better"
    if metric_name in HIGHER_IS_BETTER_METRICS:
        return "higher_is_better"
    return "neutral"


def metric_display_label(metric_name: str) -> str:
    return METRIC_DISPLAY_NAMES.get(
        metric_name,
        " ".join(part.capitalize() for part in metric_name.split("_")),
    )


def analyze_against_baseline(
    experiment_result: dict[str, Any],
    baseline_algorithm: str = "fifo",
    practical_tie_tolerance: float = DEFAULT_RELATIVE_TOLERANCE,
) -> dict[str, Any]:
    aggregated_results = experiment_result.get("results", {})
    algorithms = list(experiment_result.get("algorithms", []))
    baseline_available = baseline_algorithm in aggregated_results

    per_metric_rankings = _build_per_metric_rankings(
        aggregated_results,
        algorithms,
        practical_tie_tolerance=practical_tie_tolerance,
    )
    best_by_metric = _build_best_by_metric(per_metric_rankings)
    clinical_ranking = _build_category_ranking(
        category="clinical",
        included_metrics=CLINICAL_METRICS,
        per_metric_rankings=per_metric_rankings,
        algorithms=algorithms,
    )
    operational_ranking = _build_category_ranking(
        category="operational",
        included_metrics=OPERATIONAL_METRICS,
        per_metric_rankings=per_metric_rankings,
        algorithms=algorithms,
    )
    computational_ranking = _build_category_ranking(
        category="computational",
        included_metrics=COMPUTATIONAL_METRICS,
        per_metric_rankings=per_metric_rankings,
        algorithms=algorithms,
    )
    balanced_overall_ranking = _build_balanced_overall_ranking(
        algorithms=algorithms,
        clinical_ranking=clinical_ranking,
        operational_ranking=operational_ranking,
        computational_ranking=computational_ranking,
    )
    comparisons = _build_baseline_comparisons(
        aggregated_results=aggregated_results,
        algorithms=algorithms,
        baseline_algorithm=baseline_algorithm,
        baseline_available=baseline_available,
    )
    baseline_headline_findings = _build_baseline_headline_findings(comparisons, baseline_algorithm, baseline_available)
    headline_findings = _build_ranking_headline_findings(
        balanced_overall_ranking=balanced_overall_ranking,
        clinical_ranking=clinical_ranking,
        operational_ranking=operational_ranking,
        computational_ranking=computational_ranking,
        per_metric_rankings=per_metric_rankings,
    )
    metric_directions = {
        metric: metric_direction(metric)
        for metric in sorted(
            set().union(
                LOWER_IS_BETTER_METRICS,
                HIGHER_IS_BETTER_METRICS,
                NEUTRAL_METRICS,
            )
        )
    }
    baseline_analysis = {
        "baseline_algorithm": baseline_algorithm,
        "available": baseline_available,
        "comparisons_vs_baseline": comparisons,
        "baseline_headline_findings": baseline_headline_findings,
    }

    return {
        "clinical_ranking": clinical_ranking,
        "operational_ranking": operational_ranking,
        "computational_ranking": computational_ranking,
        "balanced_overall_ranking": balanced_overall_ranking,
        "overall_ranking": balanced_overall_ranking,
        "per_metric_rankings": per_metric_rankings,
        "headline_findings": headline_findings,
        "best_by_metric": best_by_metric,
        "baseline_analysis": baseline_analysis,
        "baseline_algorithm": baseline_algorithm,
        "baseline_available": baseline_available,
        "metric_directions": metric_directions,
        "comparisons_vs_baseline": comparisons,
        "practical_tie_tolerance": practical_tie_tolerance,
    }


def _build_per_metric_rankings(
    aggregated_results: dict[str, dict[str, dict[str, float]]],
    algorithms: list[str],
    *,
    practical_tie_tolerance: float,
) -> list[dict[str, Any]]:
    metric_names = sorted(
        {
            metric_name
            for algorithm in algorithms
            for metric_name in aggregated_results.get(algorithm, {}).keys()
        }
    )
    rankings: list[dict[str, Any]] = []
    for metric_name in metric_names:
        direction = metric_direction(metric_name)
        if direction == "neutral":
            continue
        rows = [
            {
                "algorithm": algorithm,
                "mean": round(float(summary.get("mean", 0.0)), 4),
                "std": round(float(summary.get("std", 0.0)), 4),
                "min": round(float(summary.get("min", 0.0)), 4),
                "max": round(float(summary.get("max", 0.0)), 4),
            }
            for algorithm in algorithms
            for summary in [aggregated_results.get(algorithm, {}).get(metric_name)]
            if summary is not None
        ]
        rows.sort(key=_metric_sort_key(direction))
        ranking_rows = _assign_practical_tie_ranks(
            rows,
            practical_tie_tolerance=practical_tie_tolerance,
        )
        rankings.append(
            {
                "metric_name": metric_name,
                "display_label": metric_display_label(metric_name),
                "direction": direction,
                "tolerance_used": practical_tie_tolerance,
                "ranking": ranking_rows,
            }
        )
    return rankings


def _metric_sort_key(direction: str):
    if direction == "higher_is_better":
        return lambda item: (-float(item["mean"]), item["algorithm"])
    return lambda item: (float(item["mean"]), item["algorithm"])


def _assign_practical_tie_ranks(
    rows: list[dict[str, Any]],
    *,
    practical_tie_tolerance: float,
) -> list[dict[str, Any]]:
    if not rows:
        return []

    ranked_rows: list[dict[str, Any]] = []
    current_rank = 1
    current_group = 1
    group_leader = float(rows[0]["mean"])
    ranked_rows.append(
        {
            "rank": current_rank,
            "algorithm": rows[0]["algorithm"],
            "mean": rows[0]["mean"],
            "std": rows[0]["std"],
            "min": rows[0]["min"],
            "max": rows[0]["max"],
            "practical_tie_group": current_group,
        }
    )

    for row in rows[1:]:
        current_value = float(row["mean"])
        if not _is_practical_tie(group_leader, current_value, practical_tie_tolerance):
            current_rank += 1
            current_group += 1
            group_leader = current_value
        ranked_rows.append(
            {
                "rank": current_rank,
                "algorithm": row["algorithm"],
                "mean": row["mean"],
                "std": row["std"],
                "min": row["min"],
                "max": row["max"],
                "practical_tie_group": current_group,
            }
        )
    return ranked_rows


def _is_practical_tie(reference_value: float, candidate_value: float, tolerance: float) -> bool:
    if abs(reference_value - candidate_value) <= EPSILON:
        return True
    scale = max(abs(reference_value), abs(candidate_value), EPSILON)
    return abs(reference_value - candidate_value) / scale <= tolerance


def _build_category_ranking(
    *,
    category: str,
    included_metrics: list[str],
    per_metric_rankings: list[dict[str, Any]],
    algorithms: list[str],
) -> dict[str, Any]:
    ranking_by_metric = {row["metric_name"]: row for row in per_metric_rankings}
    totals = {
        algorithm: {
            "algorithm": algorithm,
            "total_score": 0,
            "first_place_metrics": 0,
            "tied_first_place_metrics": 0,
            "metric_rank_breakdown": [],
        }
        for algorithm in algorithms
    }

    used_metrics: list[str] = []
    for metric_name in included_metrics:
        metric_ranking = ranking_by_metric.get(metric_name)
        if metric_ranking is None:
            continue
        used_metrics.append(metric_name)
        ranking_rows = metric_ranking["ranking"]
        algorithm_count = len(ranking_rows)
        first_place_group_size = sum(1 for row in ranking_rows if int(row["rank"]) == 1)
        for row in ranking_rows:
            points = algorithm_count - int(row["rank"]) + 1
            totals[row["algorithm"]]["total_score"] += points
            if int(row["rank"]) == 1:
                totals[row["algorithm"]]["first_place_metrics"] += 1
                if first_place_group_size > 1:
                    totals[row["algorithm"]]["tied_first_place_metrics"] += 1
            totals[row["algorithm"]]["metric_rank_breakdown"].append(
                {
                    "metric_name": metric_name,
                    "display_label": metric_ranking["display_label"],
                    "rank": int(row["rank"]),
                    "points": points,
                }
            )

    ordered_rows = sorted(
        totals.values(),
        key=lambda row: (
            -int(row["total_score"]),
            -int(row["first_place_metrics"]),
            row["algorithm"],
        ),
    )

    ranking_rows: list[dict[str, Any]] = []
    previous_key: tuple[int, int] | None = None
    current_rank = 0
    for ordered_index, row in enumerate(ordered_rows, start=1):
        current_key = (int(row["total_score"]), int(row["first_place_metrics"]))
        if previous_key is None or current_key != previous_key:
            current_rank = ordered_index
            previous_key = current_key
        ranking_rows.append(
            {
                "rank": current_rank,
                "algorithm": row["algorithm"],
                "total_score": int(row["total_score"]),
                "first_place_metrics": int(row["first_place_metrics"]),
                "tied_first_place_metrics": int(row["tied_first_place_metrics"]),
                "metric_rank_breakdown": sorted(
                    row["metric_rank_breakdown"],
                    key=lambda item: (
                        included_metrics.index(item["metric_name"])
                        if item["metric_name"] in included_metrics
                        else len(included_metrics),
                        item["metric_name"],
                    ),
                ),
            }
        )

    return {
        "category": category,
        "included_metrics": used_metrics,
        "ranking": ranking_rows,
    }


def _build_balanced_overall_ranking(
    *,
    algorithms: list[str],
    clinical_ranking: dict[str, Any],
    operational_ranking: dict[str, Any],
    computational_ranking: dict[str, Any],
) -> list[dict[str, Any]]:
    category_objects = {
        "clinical": clinical_ranking,
        "operational": operational_ranking,
        "computational": computational_ranking,
    }
    active_categories = {
        category: obj
        for category, obj in category_objects.items()
        if obj["included_metrics"]
    }
    active_weight_total = sum(CATEGORY_WEIGHTS[category] for category in active_categories)
    if active_weight_total <= EPSILON:
        active_weight_total = 1.0

    score_maps = {
        category: {row["algorithm"]: row for row in obj["ranking"]}
        for category, obj in category_objects.items()
    }
    normalized_category_scores = {
        category: _normalize_category_scores(obj["ranking"])
        for category, obj in category_objects.items()
    }

    rows: list[dict[str, Any]] = []
    for algorithm in algorithms:
        clinical_score = normalized_category_scores["clinical"].get(algorithm, 0.0)
        operational_score = normalized_category_scores["operational"].get(algorithm, 0.0)
        computational_score = normalized_category_scores["computational"].get(algorithm, 0.0)
        balanced_score = 0.0
        category_breakdown: list[dict[str, Any]] = []
        for category in ("clinical", "operational", "computational"):
            if category not in active_categories:
                continue
            raw_weight = CATEGORY_WEIGHTS[category]
            applied_weight = raw_weight / active_weight_total
            normalized_score = normalized_category_scores[category].get(algorithm, 0.0)
            category_row = score_maps[category].get(algorithm)
            weighted_contribution = normalized_score * applied_weight
            balanced_score += weighted_contribution
            category_breakdown.append(
                {
                    "category": category,
                    "normalized_score": round(normalized_score, 6),
                    "raw_total_score": int(category_row["total_score"]) if category_row else 0,
                    "applied_weight": round(applied_weight, 6),
                    "weighted_contribution": round(weighted_contribution, 6),
                }
            )

        rows.append(
            {
                "algorithm": algorithm,
                "balanced_score": round(balanced_score, 6),
                "clinical_score": round(clinical_score, 6),
                "operational_score": round(operational_score, 6),
                "computational_score": round(computational_score, 6),
                "category_breakdown": category_breakdown,
            }
        )

    rows.sort(
        key=lambda row: (
            -float(row["balanced_score"]),
            -float(row["clinical_score"]),
            -float(row["operational_score"]),
            -float(row["computational_score"]),
            row["algorithm"],
        )
    )

    ranked_rows: list[dict[str, Any]] = []
    previous_key: tuple[float, float, float, float] | None = None
    current_rank = 0
    for ordered_index, row in enumerate(rows, start=1):
        current_key = (
            float(row["balanced_score"]),
            float(row["clinical_score"]),
            float(row["operational_score"]),
            float(row["computational_score"]),
        )
        if previous_key is None or any(abs(a - b) > EPSILON for a, b in zip(current_key, previous_key)):
            current_rank = ordered_index
            previous_key = current_key
        ranked_rows.append(
            {
                "rank": current_rank,
                "algorithm": row["algorithm"],
                "balanced_score": row["balanced_score"],
                "clinical_score": row["clinical_score"],
                "operational_score": row["operational_score"],
                "computational_score": row["computational_score"],
                "category_breakdown": row["category_breakdown"],
            }
        )
    return ranked_rows


def _normalize_category_scores(ranking_rows: list[dict[str, Any]]) -> dict[str, float]:
    if not ranking_rows:
        return {}
    metric_count = len(ranking_rows[0]["metric_rank_breakdown"])
    algorithm_count = len(ranking_rows)
    if metric_count == 0 or algorithm_count == 0:
        return {row["algorithm"]: 0.0 for row in ranking_rows}
    max_possible_score = metric_count * algorithm_count
    if max_possible_score <= 0:
        return {row["algorithm"]: 0.0 for row in ranking_rows}
    return {
        row["algorithm"]: float(row["total_score"]) / float(max_possible_score)
        for row in ranking_rows
    }


def _build_baseline_comparisons(
    *,
    aggregated_results: dict[str, dict[str, dict[str, float]]],
    algorithms: list[str],
    baseline_algorithm: str,
    baseline_available: bool,
) -> list[dict[str, Any]]:
    if not baseline_available:
        return []

    baseline_metrics = aggregated_results[baseline_algorithm]
    rows: list[dict[str, Any]] = []
    for algorithm in algorithms:
        if algorithm == baseline_algorithm:
            continue
        algorithm_metrics = aggregated_results.get(algorithm, {})
        for metric_name, baseline_summary in baseline_metrics.items():
            direction = metric_direction(metric_name)
            algorithm_summary = algorithm_metrics.get(metric_name, {})
            baseline_mean = float(baseline_summary.get("mean", 0.0))
            algorithm_mean = float(algorithm_summary.get("mean", 0.0))
            absolute_difference = round(algorithm_mean - baseline_mean, 4)
            if direction == "neutral":
                improvement_percent = None
                status = "not_comparable"
            else:
                improvement_percent = _compute_improvement_percent(direction, baseline_mean, algorithm_mean)
                status = _classify_status(direction, baseline_mean, algorithm_mean)
            rows.append(
                {
                    "metric_name": metric_name,
                    "display_label": metric_display_label(metric_name),
                    "direction": direction,
                    "baseline_algorithm": baseline_algorithm,
                    "algorithm": algorithm,
                    "baseline_mean": round(baseline_mean, 4),
                    "algorithm_mean": round(algorithm_mean, 4),
                    "absolute_difference": absolute_difference,
                    "improvement_percent": round(improvement_percent, 4) if improvement_percent is not None else None,
                    "status": status,
                }
            )
    rows.sort(key=lambda row: (row["metric_name"], row["algorithm"]))
    return rows


def _compute_improvement_percent(direction: str, baseline_mean: float, algorithm_mean: float) -> float | None:
    if abs(baseline_mean) <= EPSILON:
        return None
    if direction == "lower_is_better":
        return ((baseline_mean - algorithm_mean) / baseline_mean) * 100.0
    return ((algorithm_mean - baseline_mean) / baseline_mean) * 100.0


def _classify_status(direction: str, baseline_mean: float, algorithm_mean: float) -> str:
    delta = algorithm_mean - baseline_mean
    if abs(delta) <= EPSILON:
        return "tied"
    if direction == "lower_is_better":
        return "improved" if algorithm_mean < baseline_mean else "regressed"
    if direction == "higher_is_better":
        return "improved" if algorithm_mean > baseline_mean else "regressed"
    return "not_comparable"


def _build_best_by_metric(per_metric_rankings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_rows: list[dict[str, Any]] = []
    for metric_ranking in per_metric_rankings:
        ranking = metric_ranking["ranking"]
        best_row = ranking[0] if ranking else None
        best_rows.append(
            {
                "metric_name": metric_ranking["metric_name"],
                "display_label": metric_ranking["display_label"],
                "direction": metric_ranking["direction"],
                "best_algorithm": best_row["algorithm"] if best_row else None,
                "best_mean": best_row["mean"] if best_row else None,
                "ranking": [
                    {
                        "rank": row["rank"],
                        "algorithm": row["algorithm"],
                        "mean": row["mean"],
                        "std": row["std"],
                        "min": row["min"],
                        "max": row["max"],
                        "practical_tie_group": row["practical_tie_group"],
                    }
                    for row in ranking
                ],
            }
        )
    return best_rows


def _build_ranking_headline_findings(
    *,
    balanced_overall_ranking: list[dict[str, Any]],
    clinical_ranking: dict[str, Any],
    operational_ranking: dict[str, Any],
    computational_ranking: dict[str, Any],
    per_metric_rankings: list[dict[str, Any]],
) -> list[str]:
    if not balanced_overall_ranking:
        return ["No comparable metrics were available to rank the selected algorithms."]

    findings: list[str] = []
    balanced_winner = balanced_overall_ranking[0]
    findings.append(
        "The balanced ranking favors the algorithm with the strongest combined clinical, operational, and computational profile."
    )
    findings.append(
        f'{balanced_winner["algorithm"].upper()} ranked first in the balanced overall ranking.'
    )

    if clinical_ranking["ranking"]:
        clinical_winner = clinical_ranking["ranking"][0]
        clinical_metric = _first_metric_won_by_algorithm(per_metric_rankings, clinical_winner["algorithm"], CLINICAL_METRICS)
        if clinical_metric:
            findings.append(
                f'{clinical_winner["algorithm"].upper()} ranked first in the clinical ranking, driven by {clinical_metric["display_label"]}.'
            )

    if computational_ranking["ranking"]:
        computational_winner = computational_ranking["ranking"][0]
        findings.append(
            f'{computational_winner["algorithm"].upper()} ranked first in computational cost because it had the lowest planning overhead.'
        )

    practical_tie_finding = _build_practical_tie_finding(per_metric_rankings)
    if practical_tie_finding:
        findings.append(practical_tie_finding)

    return findings


def _first_metric_won_by_algorithm(
    per_metric_rankings: list[dict[str, Any]],
    algorithm: str,
    candidate_metrics: list[str],
) -> dict[str, Any] | None:
    ranking_by_metric = {row["metric_name"]: row for row in per_metric_rankings}
    for metric_name in candidate_metrics:
        metric_ranking = ranking_by_metric.get(metric_name)
        if metric_ranking is None:
            continue
        top_rows = [row for row in metric_ranking["ranking"] if int(row["rank"]) == 1]
        if any(row["algorithm"] == algorithm for row in top_rows):
            return metric_ranking
    return None


def _build_practical_tie_finding(per_metric_rankings: list[dict[str, Any]]) -> str | None:
    ranking_by_metric = {row["metric_name"]: row for row in per_metric_rankings}
    for metric_name in HEADLINE_PRIORITY:
        metric_ranking = ranking_by_metric.get(metric_name)
        if metric_ranking is None:
            continue
        ranking_rows = metric_ranking["ranking"]
        if len(ranking_rows) < 2:
            continue
        first_group = [row for row in ranking_rows if row["rank"] == ranking_rows[0]["rank"]]
        if len(first_group) < 2:
            continue
        algorithm_names = " and ".join(row["algorithm"].upper() for row in first_group[:2])
        return f"{algorithm_names} were practically tied for {metric_ranking['display_label']}."
    return None


def _build_baseline_headline_findings(
    comparisons: list[dict[str, Any]],
    baseline_algorithm: str,
    baseline_available: bool,
) -> list[str]:
    if not baseline_available:
        return [f"{baseline_algorithm.upper()} baseline was not included, so baseline analysis is not available."]

    candidate_rows = [
        row
        for row in comparisons
        if row["status"] == "improved"
        and row["improvement_percent"] is not None
        and row["improvement_percent"] >= HEADLINE_THRESHOLD_PERCENT
    ]
    candidate_rows.sort(
        key=lambda row: (
            HEADLINE_PRIORITY.index(row["metric_name"]) if row["metric_name"] in HEADLINE_PRIORITY else len(HEADLINE_PRIORITY),
            -float(row["improvement_percent"]),
            row["algorithm"],
        )
    )

    findings: list[str] = []
    used_metrics: set[str] = set()
    for row in candidate_rows:
        metric_name = row["metric_name"]
        if metric_name in used_metrics:
            continue
        verb = "reduced" if metric_direction(metric_name) == "lower_is_better" else "improved"
        findings.append(
            f'{row["algorithm"]} {verb} {metric_display_label(metric_name)} by {row["improvement_percent"]:.1f}% versus FIFO'
        )
        used_metrics.add(metric_name)
        if len(findings) >= 3:
            break

    if findings:
        return findings
    return [f"No algorithm achieved a material directional improvement versus {baseline_algorithm.upper()}."]
