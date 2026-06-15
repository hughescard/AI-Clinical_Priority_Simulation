# Clinical Triage Simulator Frontend

React + Vite + TypeScript dashboard for running emergency-room simulations and algorithm comparisons.

## Install

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

The app runs by default at:

- `http://127.0.0.1:5173`

## Backend URL configuration

Default backend base URL:

- `http://127.0.0.1:8000`

Override with:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## Example workflow

1. Start the backend.
2. Start the frontend.
3. Open the dashboard in the browser.
4. Run a single simulation to inspect metrics and timeline events.
5. Run an experiment comparison to compare `fifo`, `greedy`, `astar`, and `cpsat` across multiple replications.
6. Expand Advanced Scenario Configuration when you want to override resource capacities, disable baseline resources, or enable optional resources such as `ct_scanner`.
7. In single-run results, review the active resource catalog, reported LLM provider, and cache/fallback metadata when backend enrichment metadata is present.

## Final validated configuration

The final validated project run used:

- provider: `Ollama`
- model: `llama3.2:3b`
- fallback count: `0`

`mock` remains available only for deterministic testing and controlled fallback inspection. OpenAI, Gemini, and Mistral were not used in the validated final report workflow.
