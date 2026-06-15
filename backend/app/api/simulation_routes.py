from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app.algorithms import get_algorithm as build_algorithm
from app.algorithms.base import PlanningAlgorithm
from app.config import settings
from app.evaluation.export import (
    SIMULATION_CSV_FIELDS,
    rows_to_csv,
    simulation_result_to_csv_rows,
    simulation_result_to_export_dict,
)
from app.models.simulation import (
    AdvancedScenarioConfig,
    SimulationConfig,
    SimulationResult,
    build_active_resource_catalog,
)
from app.simulation.simulator import ClinicalTriageSimulator

router = APIRouter()


class SimulationRequest(BaseModel):
    algorithm: Literal["fifo", "greedy", "astar", "cpsat", "simulated_annealing"]
    scenario: Literal["normal", "high_demand", "limited_resources"]
    seed: int
    data_source: Literal["synthetic", "mimic_iv_ed_sample", "mietic_sample", "mimic_iv_ed", "mietic"] = "synthetic"
    duration_minutes: int = Field(gt=0, le=1440)
    advanced_config: AdvancedScenarioConfig | None = None


def _get_algorithm(name: str) -> PlanningAlgorithm:
    try:
        return build_algorithm(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@router.post("/simulation/run", response_model=SimulationResult)
async def run_simulation(request: SimulationRequest) -> SimulationResult:
    return _run_simulation_from_request(request)


@router.post("/simulation/export/json")
async def export_simulation_json(request: SimulationRequest) -> JSONResponse:
    result = _run_simulation_from_request(request)
    payload = simulation_result_to_export_dict(request, result)
    filename = f"simulation_result_{request.algorithm}_{request.data_source}_seed_{request.seed}.json"
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/simulation/export/csv")
async def export_simulation_csv(request: SimulationRequest) -> Response:
    result = _run_simulation_from_request(request)
    csv_content = rows_to_csv(simulation_result_to_csv_rows(result), SIMULATION_CSV_FIELDS)
    filename = f"simulation_result_{request.algorithm}_{request.data_source}_seed_{request.seed}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _run_simulation_from_request(request: SimulationRequest) -> SimulationResult:
    algorithm = _get_algorithm(request.algorithm)
    capacities, active_catalog = build_active_resource_catalog(
        settings.default_resource_capacity.copy(),
        request.advanced_config,
    )
    config = SimulationConfig(
        algorithm=request.algorithm,
        scenario=request.scenario,
        seed=request.seed,
        data_source=request.data_source,
        duration_minutes=request.duration_minutes,
        doctor_round_interval_minutes=settings.doctor_round_interval_minutes,
        deterioration_interval_minutes=settings.deterioration_interval_minutes,
        resource_capacities=capacities,
        active_resource_catalog=active_catalog,
        advanced_config=request.advanced_config,
    )
    simulator = ClinicalTriageSimulator(config=config, algorithm=algorithm)
    try:
        return simulator.run()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
