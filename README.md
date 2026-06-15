# Clinical Triage Simulator

Academic emergency-room simulation project combining discrete-event simulation, LLM-based clinical enrichment, and AI planning algorithms.

Final validated LLM configuration:

- real provider used in the final report: `ollama`
- model: `llama3.2:3b`
- controlled fallback/testing provider only: `mock`
- OpenAI, Gemini, and Mistral were not used in the final validated experiment

## Workflows

### Backend with Docker

```bash
cp .env.example .env
docker compose up --build
```

Backend:

- `http://127.0.0.1:8000`

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Download the first local Ollama model manually:

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

Verify Ollama from the backend container:

```bash
docker compose exec backend curl http://ollama:11434/api/tags
```

### Backend local

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend local

```bash
cd frontend
npm install
npm run dev
```

Frontend:

- `http://127.0.0.1:5173`

The frontend talks to the backend at `http://127.0.0.1:8000`, including when the backend is running inside Docker.

## Running And Exporting Results

Single simulation:

```bash
curl -X POST http://127.0.0.1:8000/simulation/run \
  -H "Content-Type: application/json" \
  -d '{"algorithm":"greedy","scenario":"normal","seed":42,"data_source":"synthetic","duration_minutes":480}'
```

Experiment comparison:

```bash
curl -X POST http://127.0.0.1:8000/experiments/compare \
  -H "Content-Type: application/json" \
  -d '{"algorithms":["fifo","greedy","astar","simulated_annealing"],"scenario":"normal","seed_start":42,"data_source":"synthetic","replications":10,"duration_minutes":480}'
```

Simulation export:

```bash
curl -X POST http://127.0.0.1:8000/simulation/export/json \
  -H "Content-Type: application/json" \
  -d '{"algorithm":"greedy","scenario":"normal","seed":42,"data_source":"synthetic","duration_minutes":480}' \
  -o simulation_result.json
```

Experiment export:

```bash
curl -X POST http://127.0.0.1:8000/experiments/export/csv \
  -H "Content-Type: application/json" \
  -d '{"algorithms":["fifo","greedy","astar","simulated_annealing"],"scenario":"normal","seed_start":42,"data_source":"synthetic","replications":10,"duration_minutes":480}' \
  -o experiment_comparison.csv
```

Summary export:

```bash
curl -X POST http://127.0.0.1:8000/experiments/export/summary-csv \
  -H "Content-Type: application/json" \
  -d '{"algorithms":["fifo","greedy","astar","simulated_annealing"],"scenario":"normal","seed_start":42,"data_source":"synthetic","replications":10,"duration_minutes":480}' \
  -o experiment_summary.csv
```

Exports support the final report by preserving the request configuration, seeded reproducibility metadata, full JSON results, and CSV-ready rows for tables and figures.

## Final Experimental Validation

The final experiment runner produces report-ready outputs under `experiments/results/final_validation/...`.

Default final-validation provider:

- `LLM_PROVIDER=ollama`
- `LLM_FALLBACK_ORDER=ollama,mock`
- `OLLAMA_MODEL=llama3.2:3b`
- Docker base URL: `http://ollama:11434`
- Local base URL: `http://localhost:11434`

Quick validation:

```bash
cd backend
LLM_PROVIDER=ollama OLLAMA_BASE_URL=http://localhost:11434 OLLAMA_MODEL=llama3.2:3b OLLAMA_TIMEOUT_SECONDS=300 .venv/bin/python scripts/run_final_experiments.py --quick --use-advanced-resources --fail-on-llm-fallback --cache-path ../data/processed/llm_cache_quick_ollama_300.json
```

Full final run:

```bash
cd backend
LLM_PROVIDER=ollama OLLAMA_BASE_URL=http://localhost:11434 OLLAMA_MODEL=llama3.2:3b OLLAMA_TIMEOUT_SECONDS=300 .venv/bin/python scripts/run_final_experiments.py --use-advanced-resources --replications 10 --duration-minutes 480 --fail-on-llm-fallback --cache-path ../data/processed/llm_cache_final_ollama.json
```

If the backend is running locally outside Docker, use:

```bash
OLLAMA_BASE_URL=http://localhost:11434
```

Generated files:

- `protocol.json`
- `environment.json`
- `final_results.json`
- `final_analysis.json`
- `final_summary.csv`
- `final_metric_rankings.csv`
- `final_algorithm_rankings.csv`
- `llm_usage_summary.json`
- `README.md`

If the configured cache file already exists, the runner reuses it and prints a warning instead of deleting it.

Final validated run reference:

- data source: `MIMIC-IV-ED Demo`
- provider: `Ollama`
- model: `llama3.2:3b`
- fallback count: `0`
- total runs: `150`
- total Ollama successes: `3200`

## Patient Traceability

Single simulation results now include patient-level traceability.

Each patient trace connects:

- arrival and initial assessment
- LLM enrichment outputs such as clinical category, textual risk, required resources, and explanation
- dispatch and service-start triggers
- deterioration while waiting
- resource allocation and release
- final status, waiting time, and service time

In the frontend, patient journeys appear in the `Patient Traceability` section of simulation results with compact rows and expandable detail panels.
In JSON exports, the same information is available under `patient_traces`.

The simulation timeline also supports filtering by event type, patient, and trigger, plus text search for long runs.
These filters help inspect patient flow, blocked dispatch attempts, deterioration updates, and doctor-round replanning during development and presentation.

## Algorithm Ranking And FIFO Baseline

Experiment analysis is ranking-first, and FIFO remains available as a complementary baseline reference.

Primary outputs:

- `clinical_ranking`
- `operational_ranking`
- `computational_ranking`
- `balanced_overall_ranking`
- `overall_ranking`
- `per_metric_rankings`
- `headline_findings`
- `best_by_metric`
- `baseline_analysis`

Direction rules:

- lower is better:
  `untreated_patients`, `average_waiting_time`, `max_waiting_time`, `critical_late_patients`,
  `total_clinical_impact`, `total_planning_overhead_time`, `average_time_to_service_start`,
  `patients_deteriorated_while_waiting`, `critical_patients_waited`
- higher is better:
  `treated_patients`, `average_resource_utilization`, `critical_patients_started_immediately`,
  `services_started_from_arrival`, `services_started_from_service_end`
- neutral:
  `number_of_doctor_rounds`, `average_doctor_round_duration`, `total_doctor_round_time`,
  `number_of_initial_assessments`, `services_started_from_deterioration`,
  `services_started_from_doctor_round`, `average_time_to_initial_assessment`

Improvement versus FIFO is computed as:

- lower-is-better metrics: `((fifo_mean - algorithm_mean) / fifo_mean) * 100`
- higher-is-better metrics: `((algorithm_mean - fifo_mean) / fifo_mean) * 100`

Clinical, operational, and computational rankings are separated so low planning overhead does not dominate clinical interpretation.

Per-metric rankings use practical equivalence:

- if two means differ by less than `2%`, they are treated as a practical tie
- an absolute epsilon of `1e-9` is also used for near-zero values

Balanced overall ranking combines the category scores instead of mixing all metrics with equal weight:

- clinical: `0.50`
- operational: `0.35`
- computational: `0.15`
- category scores are normalized before weighting

Category rankings use rank-based points:

- with `N` algorithms, rank `1` receives `N` points
- rank `2` receives `N - 1` points
- the last rank receives `1` point
- tied algorithms receive the same rank and the same points
- neutral metrics are shown for context but excluded from the global score by default

This supports the final report by turning replicated experiment outputs into reproducible, direction-aware comparative findings without changing the underlying simulation behavior.

Experiment results in the frontend now also include category-based visual comparison charts:

- Clinical Performance
- Operational Efficiency
- Computational Cost
- Balanced Ranking

These charts are grouped to support final report figures and presentation discussion without replacing the underlying ranking tables or FIFO baseline comparison.

## Dataset Paths

Place the MIMIC-IV-ED demo file at:

- `data/raw/mimic-iv-ed-demo/ed/triage.csv`

Inside Docker that same file is available at:

- `/app/data/raw/mimic-iv-ed-demo/ed/triage.csv`

The compose setup mounts:

- `./backend` to `/app/backend`
- `./data` to `/app/data`

Inside Docker, always use `/app/data/...` paths for mounted datasets.

## LLM Modes

### Ollama in Docker

Ollama runs as a separate container, not inside the backend image.

- backend calls Ollama at `http://ollama:11434`
- do not use `localhost:11434` from inside the backend container
- models are stored in the `ollama_data` Docker volume
- model downloads are manual so rebuilds stay fast

Recommended first model:

- `llama3.2:3b`

Larger alternative if the machine has enough RAM/CPU:

- `llama3.1:8b`

Recommended environment values for final reproduction:

```bash
LLM_PROVIDER=ollama
LLM_FALLBACK_ORDER=ollama,mock
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_TIMEOUT_SECONDS=300
```

### Mock LLM

`mock` remains available only for deterministic tests and controlled fallback behavior. It was not used in the final validated run.

## Notes

- Backend Docker services now include `backend` and `ollama`.
- Final validated experiments used `ollama` with `--fail-on-llm-fallback`.
- Mock remains the deterministic fallback for development and test coverage.
- Legacy provider code may still remain internally for non-final compatibility, but only Ollama was used in the validated final report workflow.
- The frontend should continue to run locally with `npm run dev`.
- Do not bake model downloads into the Docker image.
- Do not commit real `.env` files, credentials, or clinical data.
