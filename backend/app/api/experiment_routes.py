from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from app.evaluation.export import (
    EXPERIMENT_RUN_CSV_FIELDS,
    EXPERIMENT_SUMMARY_CSV_FIELDS,
    experiment_result_to_csv_rows,
    experiment_result_to_export_dict,
    experiment_summary_to_csv_rows,
    rows_to_csv,
)
from app.evaluation.experiments import ExperimentComparisonRequest, run_experiment_analysis, run_experiment_comparison

router = APIRouter(prefix="/experiments")


@router.post("/compare")
async def compare_experiments(request: ExperimentComparisonRequest) -> dict:
    return _run_comparison(request)


@router.post("/analyze")
async def analyze_experiments(request: ExperimentComparisonRequest) -> dict:
    try:
        return run_experiment_analysis(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/export/json")
async def export_experiments_json(request: ExperimentComparisonRequest) -> JSONResponse:
    result = _run_comparison(request)
    payload = experiment_result_to_export_dict(request, result)
    filename = f"experiment_comparison_{request.scenario}_{request.data_source}.json"
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/export/csv")
async def export_experiments_csv(request: ExperimentComparisonRequest) -> Response:
    result = _run_comparison(request)
    csv_content = rows_to_csv(experiment_result_to_csv_rows(result), EXPERIMENT_RUN_CSV_FIELDS)
    filename = f"experiment_comparison_{request.scenario}_{request.data_source}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/export/summary-csv")
async def export_experiments_summary_csv(request: ExperimentComparisonRequest) -> Response:
    result = _run_comparison(request)
    csv_content = rows_to_csv(experiment_summary_to_csv_rows(result), EXPERIMENT_SUMMARY_CSV_FIELDS)
    filename = f"experiment_summary_{request.scenario}_{request.data_source}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _run_comparison(request: ExperimentComparisonRequest) -> dict:
    try:
        return run_experiment_comparison(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
