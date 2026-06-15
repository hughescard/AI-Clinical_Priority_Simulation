import { useState } from "react";

import { AdvancedConfigPanel } from "./AdvancedConfigPanel";
import type { Algorithm, DataSource, Scenario, SimulationRequest } from "../types";
import { formatAlgorithmName } from "../utils/algorithms";
import { buildAdvancedConfigPayload, buildResourceFormState } from "../utils/resources";

interface SimulationFormProps {
  loading: boolean;
  onSubmit: (payload: SimulationRequest) => Promise<void>;
  error: string | null;
}

const algorithms: Algorithm[] = ["fifo", "greedy", "astar", "cpsat", "simulated_annealing"];
const scenarios: Scenario[] = ["normal", "high_demand", "limited_resources"];
const dataSources: Array<{ value: DataSource; label: string }> = [
  { value: "synthetic", label: "Synthetic" },
  { value: "mimic_iv_ed_sample", label: "MIMIC-IV-ED sample" },
  { value: "mietic_sample", label: "MIETIC sample" },
  { value: "mimic_iv_ed", label: "MIMIC-IV-ED local" },
  { value: "mietic", label: "MIETIC local" },
];

export function SimulationForm({ loading, onSubmit, error }: SimulationFormProps) {
  const [form, setForm] = useState<SimulationRequest>({
    algorithm: "fifo",
    scenario: "normal",
    seed: 42,
    data_source: "synthetic",
    duration_minutes: 480,
  });
  const [showAdvancedConfig, setShowAdvancedConfig] = useState(false);
  const [resources, setResources] = useState(buildResourceFormState());

  function updateField<Key extends keyof SimulationRequest>(key: Key, value: SimulationRequest[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({
      ...form,
      advanced_config: buildAdvancedConfigPayload(resources),
    });
  }

  function updateResource(resourceId: string, updates: { enabled?: boolean; capacity?: number }) {
    setResources((current) => ({
      ...current,
      [resourceId]: {
        ...current[resourceId],
        ...updates,
      },
    }));
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="field">
          <span className="field-label">Algorithm</span>
          <select
            value={form.algorithm}
            onChange={(event) => updateField("algorithm", event.target.value as Algorithm)}
            className="field-input"
          >
            {algorithms.map((algorithm) => (
              <option key={algorithm} value={algorithm}>
                {formatAlgorithmName(algorithm)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field-label">Scenario</span>
          <select
            value={form.scenario}
            onChange={(event) => updateField("scenario", event.target.value as Scenario)}
            className="field-input"
          >
            {scenarios.map((scenario) => (
              <option key={scenario} value={scenario}>
                {scenario}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field-label">Seed</span>
          <input
            type="number"
            value={form.seed}
            onChange={(event) => updateField("seed", Number(event.target.value))}
            className="field-input"
          />
        </label>

        <label className="field">
          <span className="field-label">Data Source</span>
          <select
            value={form.data_source}
            onChange={(event) => updateField("data_source", event.target.value as DataSource)}
            className="field-input"
          >
            {dataSources.map((source) => (
              <option key={source.value} value={source.value}>
                {source.label}
              </option>
            ))}
          </select>
          <span className="text-xs text-slate-500">
            Real datasets must be placed locally and are not bundled with the project.
          </span>
        </label>

        <label className="field">
          <span className="field-label">Duration (minutes)</span>
          <input
            type="number"
            min={1}
            value={form.duration_minutes}
            onChange={(event) => updateField("duration_minutes", Number(event.target.value))}
            className="field-input"
          />
        </label>
      </div>

      <AdvancedConfigPanel
        expanded={showAdvancedConfig}
        onToggle={() => setShowAdvancedConfig((current) => !current)}
        resources={resources}
        onChange={updateResource}
      />

      <div>
        <button type="submit" disabled={loading} className="action-button">
          {loading ? "Running Simulation..." : "Run Simulation"}
        </button>
      </div>
      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}
    </form>
  );
}
