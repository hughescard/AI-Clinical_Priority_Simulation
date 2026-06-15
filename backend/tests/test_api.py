import asyncio
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

import app.api.simulation_routes as simulation_routes
from app.api.simulation_routes import (
    SimulationRequest,
    export_simulation_csv,
    export_simulation_json,
    health,
    run_simulation,
)
from app.models.simulation import SimulationResult

def test_health() -> None:
    payload = asyncio.run(health())
    assert payload["status"] == "ok"
    assert payload["service"] == "clinical-triage-simulator"


def test_run_simulation() -> None:
    result = asyncio.run(
        run_simulation(
        SimulationRequest(
            algorithm="greedy",
            scenario="normal",
            seed=42,
            duration_minutes=180,
        )
    )
    )
    assert result.algorithm == "greedy"
    assert result.scenario == "normal"
    assert result.seed == 42
    assert result.duration_minutes == 180
    assert result.data_source == "synthetic"
    assert result.dataset_name is not None
    assert result.llm_provider_requested == "mock"
    assert isinstance(result.metrics, dict)
    assert isinstance(result.resource_summary, dict)
    assert isinstance(result.patient_status_summary, dict)
    assert isinstance(result.event_counts, dict)
    assert result.llm_provider_used == "mock"
    assert result.llm_fallback_order == ["mock"]
    assert isinstance(result.llm_fallback_count, int)
    assert isinstance(result.llm_cache_hits, int)
    assert isinstance(result.llm_cache_misses, int)
    assert isinstance(result.llm_provider_attempts, dict)
    assert isinstance(result.patient_traces, list)
    assert result.patient_traces
    assert isinstance(result.timeline, list)
    assert result.active_resource_catalog


def test_run_simulation_with_advanced_config() -> None:
    result = asyncio.run(
        run_simulation(
            SimulationRequest(
                algorithm="fifo",
                scenario="normal",
                seed=42,
                duration_minutes=180,
                advanced_config={
                    "resources": [
                        {"id": "doctor", "capacity": 2, "enabled": True},
                        {"id": "pharmacy", "capacity": 1, "enabled": True},
                    ]
                },
            )
        )
    )
    assert result.active_resource_catalog["doctor"]["capacity"] == 2
    assert result.active_resource_catalog["pharmacy"]["capacity"] == 1


def test_run_simulation_astar() -> None:
    result = asyncio.run(
        run_simulation(
            SimulationRequest(
                algorithm="astar",
                scenario="normal",
                seed=42,
                duration_minutes=180,
            )
        )
    )
    assert result.algorithm == "astar"
    assert result.scenario == "normal"
    assert result.seed == 42
    assert result.duration_minutes == 180
    assert isinstance(result.metrics, dict)
    assert isinstance(result.timeline, list)


def test_run_simulation_cpsat() -> None:
    result = asyncio.run(
        run_simulation(
            SimulationRequest(
                algorithm="cpsat",
                scenario="normal",
                seed=42,
                data_source="synthetic",
                duration_minutes=180,
            )
        )
    )
    assert result.algorithm == "cpsat"
    assert result.seed == 42
    assert isinstance(result.metrics, dict)


def test_run_simulation_simulated_annealing() -> None:
    result = asyncio.run(
        run_simulation(
            SimulationRequest(
                algorithm="simulated_annealing",
                scenario="normal",
                seed=42,
                data_source="synthetic",
                duration_minutes=180,
            )
        )
    )
    assert result.algorithm == "simulated_annealing"
    assert result.seed == 42
    assert isinstance(result.metrics, dict)


def test_run_simulation_metrics_include_experiment_fields() -> None:
    result = asyncio.run(
        run_simulation(
            SimulationRequest(
                algorithm="fifo",
                scenario="normal",
                seed=42,
                duration_minutes=180,
            )
        )
    )
    assert "critical_late_patients" in result.metrics
    assert "total_clinical_impact" in result.metrics
    assert "average_resource_utilization" in result.metrics
    assert "number_of_initial_assessments" in result.metrics
    assert "services_started_from_arrival" in result.metrics
    assert "services_started_from_service_end" in result.metrics
    assert "services_started_from_deterioration" in result.metrics
    assert "services_started_from_doctor_round" in result.metrics
    assert "total_doctor_round_time" in result.metrics
    assert "number_of_doctor_rounds" in result.metrics
    assert "average_doctor_round_duration" in result.metrics
    assert "total_planning_overhead_time" in result.metrics
    assert "doctor" in result.resource_summary
    assert "TREATED" in result.patient_status_summary
    assert "INITIAL_ASSESSMENT" in result.event_counts
    assert "DOCTOR_ROUND_START" in result.event_counts


def test_run_simulation_with_mimic_sample_data_source() -> None:
    result = asyncio.run(
        run_simulation(
            SimulationRequest(
                algorithm="fifo",
                scenario="normal",
                seed=42,
                data_source="mimic_iv_ed_sample",
                duration_minutes=180,
            )
        )
    )
    assert result.scenario == "normal"
    assert result.resource_summary
    assert result.metrics["total_patients"] > 0


def _find_free_port() -> int:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]
    except PermissionError as exc:
        pytest.skip(f"Sandbox does not allow local socket binding: {exc}")


def _start_server() -> tuple[subprocess.Popen[str], str]:
    backend_root = Path(__file__).resolve().parents[1]
    port = _find_free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_root)
    process = subprocess.Popen(
        [
            str(backend_root / ".venv" / "bin" / "python"),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=backend_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("uvicorn exited before becoming ready")
        try:
            with urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return process, base_url
        except URLError:
            time.sleep(0.1)
    process.terminate()
    process.wait(timeout=5)
    raise RuntimeError("uvicorn did not become ready")


def _stop_server(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def test_health_http() -> None:
    # TestClient is unusable in this environment because Starlette's AnyIO portal hangs
    # even for a minimal FastAPI app, so this uses a real local HTTP server when allowed.
    process, base_url = _start_server()
    try:
        with urlopen(f"{base_url}/health", timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        _stop_server(process)
    assert payload == {"status": "ok", "service": "clinical-triage-simulator"}


def test_run_simulation_http() -> None:
    process, base_url = _start_server()
    try:
        request = Request(
            f"{base_url}/simulation/run",
            data=json.dumps(
                {
                    "algorithm": "greedy",
                    "scenario": "normal",
                    "seed": 42,
                    "duration_minutes": 180,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        _stop_server(process)

    assert payload["algorithm"] == "greedy"
    assert payload["scenario"] == "normal"
    assert payload["seed"] == 42
    assert payload["data_source"] == "synthetic"
    assert payload["llm_provider_requested"] == "mock"
    assert payload["llm_provider_used"] == "mock"
    assert isinstance(payload["metrics"], dict)
    assert isinstance(payload["patient_traces"], list)
    assert isinstance(payload["timeline"], list)


def test_simulation_json_export_returns_valid_json() -> None:
    response = asyncio.run(
        export_simulation_json(
            SimulationRequest(
                algorithm="fifo",
                scenario="normal",
                seed=42,
                duration_minutes=120,
            )
        )
    )
    payload = json.loads(response.body.decode("utf-8"))
    assert response.status_code == 200
    assert payload["request"]["algorithm"] == "fifo"
    assert payload["result"]["seed"] == 42
    assert "patient_traces" in payload["result"]
    assert "generated_at" in payload
    assert "attachment;" in response.headers["content-disposition"]


def test_simulation_json_export_preserves_dispatch_attempt_and_live_round_end_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeline = [
        {
            "time": 10.6,
            "event_type": "DOCTOR_ROUND_END",
            "trigger": "doctor_round_replan",
            "waiting_patient_count": 3,
            "active_patient_count": 1,
            "active_service_count": 1,
            "round_duration": 0.6,
            "planning_overhead": 0.1,
            "algorithm": "fifo",
            "resources": {},
        },
        {
            "time": 10.6,
            "event_type": "DISPATCH_ATTEMPT",
            "trigger": "doctor_round_replan",
            "algorithm": "fifo",
            "waiting_patient_count": 3,
            "active_patient_count": 1,
            "active_service_count": 1,
            "available_resources": {"doctor": 0, "nurse": 1},
            "feasible_patient_count": 0,
            "started_patient_count": 0,
            "blocking_resources": ["doctor"],
            "message": "No feasible waiting patient could be started with current available resources.",
            "resources": {},
        },
    ]
    fake_result = SimulationResult(
        algorithm="fifo",
        scenario="normal",
        seed=42,
        duration_minutes=120,
        data_source="synthetic",
        dataset_name="Synthetic Scenario Generator",
        metrics={"treated_patients": 0},
        resource_summary={},
        patient_status_summary={},
        event_counts={"DOCTOR_ROUND_END": 1, "DISPATCH_ATTEMPT": 1},
        timeline=timeline,
    )
    monkeypatch.setattr(simulation_routes, "_run_simulation_from_request", lambda request: fake_result)

    response = asyncio.run(
        export_simulation_json(
            SimulationRequest(
                algorithm="fifo",
                scenario="normal",
                seed=42,
                duration_minutes=120,
            )
        )
    )
    payload = json.loads(response.body.decode("utf-8"))

    events = payload["result"]["timeline"]
    round_end = next(event for event in events if event["event_type"] == "DOCTOR_ROUND_END")
    dispatch_attempt = next(event for event in events if event["event_type"] == "DISPATCH_ATTEMPT")
    assert round_end["waiting_patient_count"] == 3
    assert round_end["active_service_count"] == 1
    assert dispatch_attempt["blocking_resources"] == ["doctor"]
    assert dispatch_attempt["available_resources"] == {"doctor": 0, "nurse": 1}
    assert dispatch_attempt["message"] == "No feasible waiting patient could be started with current available resources."


def test_simulation_csv_export_returns_csv_headers() -> None:
    response = asyncio.run(
        export_simulation_csv(
            SimulationRequest(
                algorithm="greedy",
                scenario="normal",
                seed=42,
                duration_minutes=120,
            )
        )
    )
    content = response.body.decode("utf-8")
    assert response.status_code == 200
    assert response.media_type == "text/csv"
    assert "algorithm,scenario,data_source,seed,duration_minutes" in content.splitlines()[0]
    assert "llm_provider_requested" in content.splitlines()[0]
    assert "number_of_initial_assessments" in content.splitlines()[0]
    assert "services_started_from_arrival" in content.splitlines()[0]
    assert "patients_deteriorated_while_waiting" in content.splitlines()[0]
