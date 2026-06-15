# clinical-triage-simulator backend

Backend foundation for an academic emergency-room simulation system that compares clinical prioritization algorithms under limited resources.

## Implemented in this version

- FastAPI backend with `GET /health`, `POST /simulation/run`, and `POST /experiments/compare`
- Core domain models for patients, resources, simulation state, and events
- Seeded scenario generator for deterministic simulations
- Deterministic mock LLM clinical enrichment module
- Local dataset ingestion layer for synthetic, sample, and configured CSV-backed emergency data
- Minimal discrete-event simulator with arrivals, deterioration, doctor rounds, service start/end, and resource release
- Continuous operational dispatch:
  arrivals trigger initial assessment,
  service completion triggers immediate backfill dispatch,
  deterioration can trigger reassessment when resources are free,
  and doctor rounds remain non-instantaneous global replanning events
- FIFO and Dynamic Greedy planning algorithms
- A* local planning algorithm over a bounded candidate window
- CP-SAT optimization planner over a bounded candidate window using OR-Tools
- Basic evaluation metrics
- Automated tests with `pytest`
- Placeholder-ready architecture for adding future algorithms such as A*

## Project structure

```text
backend/
  app/
  tests/
  requirements.txt
  README.md
```

Additional folders were created at the repository root for `data/`, `experiments/`, and `report/`.

## Clinical Enrichment

Generated patients are enriched through a provider layer in `app/llm/provider.py`.

Final validated provider scope:

- `ollama` local structured-output extraction through the Ollama HTTP API
- `mock` deterministic keyword rules used only for tests and controlled fallback behavior

The final validated report run used Ollama only. Legacy provider code may still remain in the repository for compatibility and older tests, but it was not used in the validated final experiment.

Enrichment fields:

- `key_symptoms`
- `textual_risk_score`
- `clinical_category`
- `deterioration_rate`
- `max_wait_time`
- `estimated_service_time`
- `required_resources`
- `explanation`

Environment variables:

- `LLM_PROVIDER` optional, final validated value `ollama`
- `OLLAMA_BASE_URL` optional, local default `http://localhost:11434`
- `OLLAMA_MODEL` optional, default `llama3.2:3b`
- `OLLAMA_TIMEOUT_SECONDS` optional, recommended `300` for final validation runs
- `LLM_FALLBACK_TO_MOCK` optional, default `true`
- `LLM_CACHE_PATH` optional file cache path

Cache keys include:

- provider
- model
- schema version
- chief complaint
- clinical description

This prevents collisions between mock and Ollama enrichments for the same text in the final validated workflow.

Safety notes:

- outputs are used only to estimate simulation variables
- outputs are not medical diagnosis or treatment advice
- do not send sensitive real patient data unless you are properly authorized to do so
- automated tests do not require API keys and do not make real API calls

Advanced resource-aware prompting:

- every provider receives the active resource catalog for the current run
- prompts include each active resource id, enabled state, effective capacity, and a short clinical use case
- optional resources such as `ct_scanner`, `xray_room`, `ultrasound_room`, `isolation_room`, `pharmacy`, and `specialist` are recommended only when clinically justified
- disabled resources are not offered to the LLM and cannot be selected in `required_resources`
- enabled resources with capacity `0` are still shown to the LLM as clinically valid resources, but marked as currently unavailable
- zero-capacity enabled resources may still appear in `required_resources`, which allows bottleneck experiments and blocking-resource analysis

Run with mock provider:

```bash
export LLM_PROVIDER=mock
uvicorn app.main:app --reload
```

Run with final validated provider:

```bash
export LLM_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.2:3b
export OLLAMA_TIMEOUT_SECONDS=300
export LLM_FALLBACK_TO_MOCK=true
uvicorn app.main:app --reload
```

## Data Sources

The simulator supports an optional `data_source` field in simulation and experiment requests.

Supported values:

- `synthetic`
- `mimic_iv_ed_sample`
- `mietic_sample`
- `mimic_iv_ed`
- `mietic`

Default:

- `synthetic`

Use synthetic data:

```json
{
  "algorithm": "fifo",
  "scenario": "normal",
  "seed": 42,
  "data_source": "synthetic",
  "duration_minutes": 480
}
```

Use bundled safe sample CSVs:

```json
{
  "algorithm": "greedy",
  "scenario": "normal",
  "seed": 42,
  "data_source": "mimic_iv_ed_sample",
  "duration_minutes": 480
}
```

Real local dataset configuration:

- set `MIMIC_IV_ED_TRIAGE_CSV` for `data_source="mimic_iv_ed"`
- set `MIETIC_CSV` for `data_source="mietic"`

Example:

```bash
export MIMIC_IV_ED_TRIAGE_CSV=/path/to/triage.csv
export MIETIC_CSV=/path/to/mietic.csv
```

Important:

- do not commit real clinical data into this repository
- this project does not download datasets automatically
- MIMIC-IV-ED access may require PhysioNet training/credentialing outside this project

## Planning Algorithms

Available planners:

- `fifo`
- `greedy`
- `astar`
- `cpsat`
- `simulated_annealing`

The current A* implementation solves a local doctor-round ordering problem over the top `K` waiting candidates, with deterministic costs and heuristics. It does not simulate the full emergency room; it only decides a clinically informed service-start order for the current planning moment.

The CP-SAT planner is the advanced optimization baseline. It also solves a bounded local doctor-round problem rather than the full emergency room. It uses OR-Tools to select a feasible high-utility batch under current resource constraints, then appends remaining patients in deterministic Greedy order.

A* vs CP-SAT:

- `astar` explores an informed search tree over candidate orderings
- `cpsat` builds a bounded constraint optimization model over the current queue snapshot
- both are local doctor-round planners, not full-trajectory simulators

Simulated Annealing:

- `simulated_annealing` starts from the deterministic Greedy order, optimizes a bounded planning window with seeded neighborhood moves, and appends remaining patients in deterministic order
- it balances urgency, lateness, deterioration, service time, and resource feasibility without simulating the full emergency room inside the planner

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```

## Final Experimental Validation

The final validation runner writes report-ready outputs under `../experiments/results/final_validation/...`.

Default final-validation provider:

- `LLM_PROVIDER=ollama`
- `LLM_FALLBACK_ORDER=ollama,mock`
- `OLLAMA_MODEL=llama3.2:3b`
- Docker base URL: `http://ollama:11434`
- Local base URL: `http://localhost:11434`
- Default final cache path in Docker: `/app/data/processed/llm_cache_final_ollama.json`

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

If you are running outside Docker, use:

```bash
OLLAMA_BASE_URL=http://localhost:11434
```

Final validated run reference:

- data source: `MIMIC-IV-ED Demo`
- provider: `Ollama`
- model: `llama3.2:3b`
- fallback count: `0`
- total runs: `150`
- total Ollama successes: `3200`

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

If the selected cache file already exists, the runner warns and reuses it. It does not delete the cache automatically.

## API

### `GET /health`

Returns service status.

### `POST /simulation/run`

Request body:

```json
{
  "algorithm": "fifo",
  "scenario": "normal",
  "seed": 42,
  "data_source": "synthetic",
  "duration_minutes": 480
}
```

Optional advanced resource override:

```json
{
  "algorithm": "fifo",
  "scenario": "normal",
  "seed": 42,
  "data_source": "synthetic",
  "duration_minutes": 480,
  "advanced_config": {
    "resources": [
      { "id": "doctor", "capacity": 2, "enabled": true },
      { "id": "nurse", "capacity": 0, "enabled": false },
      { "id": "ct_scanner", "capacity": 1, "enabled": true }
    ]
  }
}
```

Response body includes:

- `algorithm`
- `scenario`
- `seed`
- `metrics`
- `patient_traces`
- `timeline`

`patient_traces` support patient-level explainability for single runs by linking enrichment outputs, waiting reasons, deterioration, service triggers, resources, and final outcomes for each patient.

`advanced_config` is optional. When present, it selectively overrides the active resource catalog after the scenario preset is applied. Resource ids must be lowercase snake_case. Disabled resources remain visible in outputs with zero effective capacity so blocking behavior stays traceable.

Resource semantics:

- `enabled=false`: the resource is not part of the scenario, is excluded from prompts, and is rejected by validation
- `enabled=true` with `capacity=0`: the resource is part of the scenario, is shown to the LLM as clinically valid but currently unavailable, is accepted by validation, and can appear as a blocking resource during dispatch

### `POST /experiments/compare`

Request body:

```json
{
  "algorithms": ["fifo", "greedy", "astar", "simulated_annealing"],
  "scenario": "normal",
  "seed_start": 42,
  "data_source": "synthetic",
  "replications": 10,
  "duration_minutes": 480
}
```

The same optional `advanced_config` block may be sent for experiment runs. Every replication then uses the same scenario preset, duration, data source, and advanced resource overrides, while seeds still advance deterministically from `seed_start`.

## Manual Verification For Optional Resources

1. Enable optional resources in `advanced_config`:
   - `xray_room`
   - `ct_scanner`
   - `ultrasound_room`
   - `isolation_room`
   - `pharmacy`
   - `specialist`
2. Run with:
   - `LLM_PROVIDER=ollama`
   - `scenario=high_demand`
   - `algorithm=greedy`
   - `duration_minutes=120` or `240`
3. Clear cache before the first run:

```bash
rm -f data/processed/llm_cache*.json
```

4. Inspect:
   - Patient Traceability: `required_resources` should include optional resources for clinically relevant cases
   - Active Resource Catalog: optional resources should show utilization if they were allocated
   - Timeline: `blocking_resources` may include optional resources when they are active but unavailable

This runs each requested algorithm across the seed sequence:

- `42`
- `43`
- `44`
- ...

using the same scenario parameters, same duration, same resource configuration, and the same seed schedule.

Important:

- algorithms are compared under the same initial experimental conditions
- they are not guaranteed to produce the same trajectory, because planning decisions change the dynamic simulation over time

The comparison response includes individual run metrics plus aggregated `mean`, `std`, `min`, and `max` summaries.

### `POST /experiments/analyze`

Uses the same request body as `POST /experiments/compare`, but returns a ranking-first interpretation layer plus a complementary FIFO baseline analysis when `fifo` is included.

The analysis response includes:

- clinical ranking
- operational ranking
- computational cost ranking
- balanced overall ranking
- backward-compatible `overall_ranking` aliasing the balanced ranking
- per-metric rankings
- deterministic headline findings
- best algorithm by directed metric
- per-algorithm comparisons versus FIFO inside `baseline_analysis`

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

Improvement percentage versus FIFO is computed as:

- lower-is-better: `((fifo_mean - algorithm_mean) / fifo_mean) * 100`
- higher-is-better: `((algorithm_mean - fifo_mean) / fifo_mean) * 100`

When the FIFO mean is zero, percentage improvement is reported as `null` to avoid division by zero.

Clinical, operational, and computational rankings each use rank-based points:

- with `N` algorithms, rank `1` receives `N` points
- rank `2` receives `N - 1` points
- the last rank receives `1` point
- tied algorithms receive the same rank and the same points

Practical equivalence:

- per-metric rankings treat algorithms as practically tied when their relative mean difference is within `2%`
- an absolute epsilon of `1e-9` is also used for near-zero values
- this prevents tiny numerical differences from dominating category rankings

Balanced overall ranking:

- clinical weight: `0.50`
- operational weight: `0.35`
- computational weight: `0.15`
- each category score is normalized to `0-1` within its category scale before weighting
- if a category has no valid metrics, remaining weights are renormalized

Neutral metrics are shown for context but excluded from clinical, operational, computational, and balanced ranking scores by default.

### Export Endpoints

Simulation exports use the same request body as `POST /simulation/run`:

- `POST /simulation/export/json`
- `POST /simulation/export/csv`

Experiment exports use the same request body as `POST /experiments/compare`:

- `POST /experiments/export/json`
- `POST /experiments/export/csv`
- `POST /experiments/export/summary-csv`

JSON exports include:

- original request configuration
- generated timestamp
- reproducibility metadata such as algorithms, seeds, scenario, and duration
- full result payloads

CSV exports include:

- per-run simulation or experiment rows for report tables
- per-algorithm summary rows with `mean`, `std`, `min`, and `max`

Use exported JSON/CSV files to reproduce tables and figures in the final report.

## Doctor Rounds

Doctor rounds are now simulated as non-instantaneous events.

Behavior:

- `DOCTOR_ROUND_START` occurs at the configured interval
- the simulator computes a round duration from:
  - base round duration
  - waiting-patient review time
  - algorithm planning overhead
- `DOCTOR_ROUND_END` is scheduled at `start + duration`
- planning is executed only at `DOCTOR_ROUND_END`
- deterioration updates and service completions can still happen while the round is in progress

Simulated planning overhead:

- `fifo`: `0.1` minutes
- `greedy`: `0.3` minutes
- `astar`: depends on planning window size, default `1.0` minute
- `simulated_annealing`: `1.5` minutes

Doctor-round-related metrics now include:

- `total_doctor_round_time`
- `number_of_doctor_rounds`
- `average_doctor_round_duration`
- `total_planning_overhead_time`

## Running

Single simulation:

```bash
curl -X POST http://127.0.0.1:8000/simulation/run \
  -H "Content-Type: application/json" \
  -d '{"algorithm":"cpsat","scenario":"normal","seed":42,"data_source":"synthetic","duration_minutes":480}'
```

Experiment comparison:

```bash
curl -X POST http://127.0.0.1:8000/experiments/compare \
  -H "Content-Type: application/json" \
  -d '{"algorithms":["fifo","greedy","astar","simulated_annealing"],"scenario":"high_demand","seed_start":42,"data_source":"synthetic","replications":10,"duration_minutes":480}'
```

Simulation CSV export:

```bash
curl -X POST http://127.0.0.1:8000/simulation/export/csv \
  -H "Content-Type: application/json" \
  -d '{"algorithm":"greedy","scenario":"normal","seed":42,"data_source":"synthetic","duration_minutes":480}' \
  -o simulation_result.csv
```

Experiment summary CSV export:

```bash
curl -X POST http://127.0.0.1:8000/experiments/export/summary-csv \
  -H "Content-Type: application/json" \
  -d '{"algorithms":["fifo","greedy","astar","simulated_annealing"],"scenario":"high_demand","seed_start":42,"data_source":"synthetic","replications":10,"duration_minutes":480}' \
  -o experiment_summary.csv
```

## Notes

- All randomness is controlled with a seed.
- The frontend is available under `../frontend`.
- Local development can still use the deterministic mock extractor, but the final validated configuration uses Ollama only.
- OpenAI, Gemini, and Mistral were not used in the final validated experiment.
