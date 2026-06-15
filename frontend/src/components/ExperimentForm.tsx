import { useState } from "react";

import { AdvancedConfigPanel } from "./AdvancedConfigPanel";
import type { Algorithm, DataSource, ExperimentComparisonRequest, Scenario } from "../types";
import { formatAlgorithmName } from "../utils/algorithms";
import { buildAdvancedConfigPayload, buildResourceFormState } from "../utils/resources";

interface ExperimentFormProps {
  loading: boolean;
  onSubmit: (payload: ExperimentComparisonRequest) => Promise<void>;
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

export function ExperimentForm({ loading, onSubmit, error }: ExperimentFormProps) {
  const [form, setForm] = useState<ExperimentComparisonRequest>({
    algorithms,
    scenario: "normal",
    seed_start: 42,
    data_source: "synthetic",
    replications: 10,
    duration_minutes: 480,
  });
  const [showAdvancedConfig, setShowAdvancedConfig] = useState(false);
  const [resources, setResources] = useState(buildResourceFormState());

  function toggleAlgorithm(algorithm: Algorithm) {
    setForm((current) => {
      const exists = current.algorithms.includes(algorithm);
      const nextAlgorithms = exists
        ? current.algorithms.filter((item) => item !== algorithm)
        : [...current.algorithms, algorithm];
      return { ...current, algorithms: nextAlgorithms };
    });
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
      <div>
        <p className="field-label">Algorithms</p>
        <div className="mt-3 flex flex-wrap gap-3">
          {algorithms.map((algorithm) => {
            const selected = form.algorithms.includes(algorithm);
            return (
              <label
                key={algorithm}
                className={`inline-flex cursor-pointer items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium ${
                  selected
                    ? "border-emerald-500 bg-emerald-50 text-emerald-900"
                    : "border-slate-200 bg-white text-slate-700"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={() => toggleAlgorithm(algorithm)}
                  className="h-4 w-4 accent-emerald-600"
                />
                {formatAlgorithmName(algorithm)}
              </label>
            );
          })}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="field">
          <span className="field-label">Scenario</span>
          <select
            value={form.scenario}
            onChange={(event) => setForm((current) => ({ ...current, scenario: event.target.value as Scenario }))}
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
          <span className="field-label">Seed Start</span>
          <input
            type="number"
            value={form.seed_start}
            onChange={(event) => setForm((current) => ({ ...current, seed_start: Number(event.target.value) }))}
            className="field-input"
          />
        </label>

        <label className="field">
          <span className="field-label">Data Source</span>
          <select
            value={form.data_source}
            onChange={(event) => setForm((current) => ({ ...current, data_source: event.target.value as DataSource }))}
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
          <span className="field-label">Replications</span>
          <input
            type="number"
            min={1}
            value={form.replications}
            onChange={(event) => setForm((current) => ({ ...current, replications: Number(event.target.value) }))}
            className="field-input"
          />
        </label>

        <label className="field">
          <span className="field-label">Duration (minutes)</span>
          <input
            type="number"
            min={1}
            value={form.duration_minutes}
            onChange={(event) => setForm((current) => ({ ...current, duration_minutes: Number(event.target.value) }))}
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

      <button type="submit" disabled={loading || form.algorithms.length === 0} className="action-button">
        {loading ? "Running Comparison..." : "Run Comparison"}
      </button>
      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}
    </form>
  );
}
