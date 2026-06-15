import { ActiveResourceCatalogPanel } from "./ActiveResourceCatalogPanel";
import { AlgorithmBadge } from "./AlgorithmBadge";
import { AlgorithmGuide } from "./AlgorithmGuide";
import { DoctorRoundPanel } from "./DoctorRoundPanel";
import { MetricCard } from "./MetricCard";
import { PatientTraceability } from "./PatientTraceability";
import { ResourceSummaryPanel } from "./ResourceSummaryPanel";
import { Timeline } from "./Timeline";
import type { SimulationRequest, SimulationResponse } from "../types";
import { formatProviderName } from "../utils/providers";

interface SimulationResultsProps {
  result: SimulationResponse;
  request: SimulationRequest;
  onDownloadJson: (payload: SimulationRequest) => Promise<void>;
  onDownloadCsv: (payload: SimulationRequest) => Promise<void>;
  exportError: string | null;
}

export function SimulationResults({
  result,
  request,
  onDownloadJson,
  onDownloadCsv,
  exportError,
}: SimulationResultsProps) {
  const { metrics } = result;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <AlgorithmBadge algorithm={result.algorithm} />
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
            Scenario: {result.scenario}
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
            Seed: {result.seed}
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
            Duration: {result.duration_minutes} min
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
            Data source: {result.data_source}
          </span>
          {result.dataset_records_used !== null && result.dataset_records_used !== undefined ? (
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
              Dataset records: {result.dataset_records_used}
            </span>
          ) : null}
          {result.dataset_name ? (
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
              Source: {result.dataset_name}
            </span>
          ) : null}
          {result.llm_provider_requested ? (
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
              LLM requested: {formatProviderName(result.llm_provider_requested)}
            </span>
          ) : null}
          {result.llm_provider_used ? (
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
              LLM used: {formatProviderName(result.llm_provider_used)}
            </span>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="action-button" onClick={() => void onDownloadJson(request)}>
            Download JSON
          </button>
          <button type="button" className="action-button" onClick={() => void onDownloadCsv(request)}>
            Download CSV
          </button>
        </div>
      </div>

      {exportError ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {exportError}
        </div>
      ) : null}

      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
        Use exported JSON/CSV files to reproduce tables and figures in the final report.
      </div>

      {result.llm_provider_used ? (
        <div className="grid gap-4 md:grid-cols-5">
          <MetricCard label="LLM Fallbacks" value={result.llm_fallback_count ?? 0} accent="warning" />
          <MetricCard label="LLM Cache Hits" value={result.llm_cache_hits ?? 0} accent="success" />
          <MetricCard label="LLM Cache Misses" value={result.llm_cache_misses ?? 0} />
          <MetricCard label="Provider Attempts" value={formatProviderAttempts(result.llm_provider_attempts)} />
          <MetricCard label="Provider Retries" value={formatProviderRetries(result.llm_provider_retries)} />
        </div>
      ) : null}

      {result.llm_fallback_order && result.llm_fallback_order.length > 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          Fallback order: <span className="font-semibold">{result.llm_fallback_order.join(" -> ")}</span>
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Treated Patients" value={metrics.treated_patients} accent="success" />
        <MetricCard label="Untreated Patients" value={metrics.untreated_patients} accent="danger" />
        <MetricCard label="Average Waiting Time" value={metrics.average_waiting_time.toFixed(2)} />
        <MetricCard label="Max Waiting Time" value={metrics.max_waiting_time.toFixed(2)} accent="warning" />
        <MetricCard label="Critical Late Patients" value={metrics.critical_late_patients} accent="danger" />
        <MetricCard label="Clinical Impact" value={metrics.total_clinical_impact.toFixed(2)} />
        <MetricCard label="Resource Utilization" value={`${(metrics.average_resource_utilization * 100).toFixed(1)}%`} />
        <MetricCard label="Doctor Rounds" value={metrics.number_of_doctor_rounds} />
        <MetricCard label="Avg Round Duration" value={metrics.average_doctor_round_duration.toFixed(2)} />
        <MetricCard label="Total Round Time" value={metrics.total_doctor_round_time.toFixed(2)} />
        <MetricCard label="Planning Overhead" value={metrics.total_planning_overhead_time.toFixed(2)} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <DoctorRoundPanel metrics={metrics} />
        <AlgorithmGuide />
      </div>

      <ResourceSummaryPanel resources={result.resource_summary} />

      <ActiveResourceCatalogPanel
        activeCatalog={result.active_resource_catalog}
        resourceSummary={result.resource_summary}
      />

      <PatientTraceability patientTraces={result.patient_traces} />

      <Timeline events={result.timeline} />
    </section>
  );
}

function formatProviderAttempts(
  attempts?: Record<string, { successes: number; failures: number }>,
) {
  if (!attempts || Object.keys(attempts).length === 0) {
    return "n/a";
  }
  return Object.entries(attempts)
    .map(([provider, stats]) => `${formatProviderName(provider)} S${stats.successes}/F${stats.failures}`)
    .join(" | ");
}

function formatProviderRetries(retries?: Record<string, number>) {
  if (!retries || Object.keys(retries).length === 0) {
    return "n/a";
  }
  return Object.entries(retries)
    .map(([provider, count]) => `${formatProviderName(provider)} R${count}`)
    .join(" | ");
}
