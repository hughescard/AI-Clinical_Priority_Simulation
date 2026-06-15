import { useEffect, useMemo, useState } from "react";

import type { PatientTrace } from "../types";
import { formatAlgorithmName } from "../utils/algorithms";
import { formatProviderName } from "../utils/providers";

interface PatientTraceabilityProps {
  patientTraces: PatientTrace[];
}

type TraceFilter = "all" | "treated" | "untreated" | "deteriorated" | "critical_waiting" | "immediate_service";
type TraceSort = "arrival" | "waiting_desc" | "risk_desc";

const FILTER_OPTIONS: Array<{ value: TraceFilter; label: string }> = [
  { value: "all", label: "All patients" },
  { value: "treated", label: "Treated" },
  { value: "untreated", label: "Untreated" },
  { value: "deteriorated", label: "Deteriorated" },
  { value: "critical_waiting", label: "Critical waiting" },
  { value: "immediate_service", label: "Immediate service" },
];

const SORT_OPTIONS: Array<{ value: TraceSort; label: string }> = [
  { value: "arrival", label: "Arrival time" },
  { value: "waiting_desc", label: "Waiting time descending" },
  { value: "risk_desc", label: "Risk descending" },
];

export function PatientTraceability({ patientTraces }: PatientTraceabilityProps) {
  const [filter, setFilter] = useState<TraceFilter>("all");
  const [sort, setSort] = useState<TraceSort>("arrival");

  const visibleTraces = useMemo(() => {
    const filtered = patientTraces.filter((trace) => {
      if (filter === "all") return true;
      if (filter === "treated") return trace.final_status === "TREATED";
      if (filter === "untreated") return trace.final_status !== "TREATED";
      if (filter === "deteriorated") return trace.deteriorated_while_waiting;
      if (filter === "critical_waiting") return trace.critical_waiting;
      if (filter === "immediate_service") return trace.immediate_service;
      return true;
    });

    return filtered.sort((left, right) => {
      if (sort === "waiting_desc") {
        return (right.waiting_time ?? -1) - (left.waiting_time ?? -1) || left.patient_id.localeCompare(right.patient_id);
      }
      if (sort === "risk_desc") {
        return (right.risk_level ?? -1) - (left.risk_level ?? -1) || left.patient_id.localeCompare(right.patient_id);
      }
      return left.arrival_time - right.arrival_time || left.patient_id.localeCompare(right.patient_id);
    });
  }, [filter, patientTraces, sort]);

  useEffect(() => {
    function focusTraceFromHash() {
      const hash = window.location.hash;
      if (!hash.startsWith("#patient-trace-")) {
        return;
      }
      const element = document.getElementById(hash.slice(1));
      if (!(element instanceof HTMLDetailsElement)) {
        return;
      }
      element.open = true;
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    focusTraceFromHash();
    window.addEventListener("hashchange", focusTraceFromHash);
    return () => window.removeEventListener("hashchange", focusTraceFromHash);
  }, [visibleTraces]);

  return (
    <div className="panel p-5">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-xl font-semibold text-slate-950">Patient Traceability</h3>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Inspect how enrichment, dispatch decisions, resource limits, deterioration, and final outcomes affected each patient journey.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {FILTER_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`rounded-full px-3 py-1.5 text-sm font-medium ${
                filter === option.value
                  ? "bg-emerald-100 text-emerald-900"
                  : "bg-slate-100 text-slate-700"
              }`}
              onClick={() => setFilter(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <span className="text-sm text-slate-600">{visibleTraces.length} patients shown</span>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          Sort by
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as TraceSort)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="space-y-3">
        {visibleTraces.map((trace, index) => (
          <details
            key={trace.patient_id}
            id={`patient-trace-${trace.patient_id}`}
            open={index === 0}
            className="group rounded-2xl border border-slate-200 bg-white"
          >
            <summary className="flex cursor-pointer list-none flex-wrap items-start justify-between gap-4 p-4">
              <div className="grid min-w-0 flex-1 gap-3 md:grid-cols-5 xl:grid-cols-10">
                <TraceCell label="Patient" value={trace.patient_id} strong />
                <TraceCell label="Status" value={formatStatusLabel(trace.final_status)} badge={statusStyle(trace.final_status)} />
                <TraceCell label="Category" value={trace.clinical_category ?? "n/a"} />
                <TraceCell label="Risk" value={formatRisk(trace)} />
                <TraceCell label="Arrival" value={formatMinutes(trace.arrival_time)} />
                <TraceCell label="Service Start" value={formatOptionalMinutes(trace.service_start_time)} />
                <TraceCell label="Waiting Time" value={formatOptionalMinutes(trace.waiting_time)} />
                <TraceCell label="Service Trigger" value={formatTrigger(trace.service_start_trigger)} />
                <TraceCell label="Deteriorated" value={trace.deteriorated_while_waiting ? "Yes" : "No"} />
                <TraceCell label="Required Resources" value={formatResourceList(trace.required_resources)} />
              </div>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-sm font-medium text-slate-700 transition-transform group-open:rotate-90">
                &rsaquo;
              </span>
            </summary>

            <div className="border-t border-slate-200 px-4 pb-4 pt-3">
              <div className="grid gap-4 xl:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Journey Summary
                  </h4>
                  <div className="space-y-2 text-sm text-slate-700">
                    <p>Initial assessment: <span className="font-medium">{formatOptionalMinutes(trace.initial_assessment_time)}</span></p>
                    <p>Time to assessment: <span className="font-medium">{formatOptionalMinutes(trace.time_to_initial_assessment)}</span></p>
                    <p>Service end: <span className="font-medium">{formatOptionalMinutes(trace.service_end_time)}</span></p>
                    <p>Service time: <span className="font-medium">{formatOptionalMinutes(trace.service_time)}</span></p>
                    <p>Algorithm: <span className="font-medium">{formatAlgorithmName(trace.algorithm)}</span></p>
                    <p>Immediate service: <span className="font-medium">{trace.immediate_service ? "Yes" : "No"}</span></p>
                    <p>Critical waiting: <span className="font-medium">{trace.critical_waiting ? "Yes" : "No"}</span></p>
                  </div>
                </div>

                <div className="rounded-2xl bg-slate-50 p-4">
                  <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Enrichment & Resources
                  </h4>
                  <div className="space-y-2 text-sm text-slate-700">
                    <p>LLM provider: <span className="font-medium">{formatProviderName(trace.llm_provider_used)}</span></p>
                    <p>Textual risk: <span className="font-medium">{trace.textual_risk_score ?? "n/a"}</span></p>
                    <p>Deterioration rate: <span className="font-medium">{trace.deterioration_rate ?? "n/a"}</span></p>
                    <p>Max wait time: <span className="font-medium">{trace.max_wait_time ?? "n/a"}</span></p>
                    <p>Estimated service time: <span className="font-medium">{trace.estimated_service_time ?? "n/a"}</span></p>
                    <p>Required resources: <span className="font-medium">{formatResourceList(trace.required_resources)}</span></p>
                    <p>Allocated resources: <span className="font-medium">{formatResourceList(trace.allocated_resources)}</span></p>
                    <p>Released resources: <span className="font-medium">{formatResourceList(trace.resources_released)}</span></p>
                  </div>
                </div>
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Deterioration & Waiting
                  </h4>
                  <div className="space-y-2 text-sm text-slate-700">
                    <p>Deterioration events: <span className="font-medium">{trace.deterioration_events_count}</span></p>
                    <p>Deterioration times: <span className="font-medium">{trace.deterioration_times.length > 0 ? trace.deterioration_times.map(formatMinutes).join(", ") : "None"}</span></p>
                    <p>Timeline references: <span className="font-medium">{trace.timeline_event_ids.length > 0 ? trace.timeline_event_ids.join(", ") : "None"}</span></p>
                  </div>
                  {trace.waiting_reason_events.length > 0 ? (
                    <div className="mt-3 space-y-2">
                      {trace.waiting_reason_events.map((reason, index) => (
                        <div key={`${trace.patient_id}-reason-${index}`} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
                          <p className="font-medium">{formatMinutes(reason.time)} · {formatTrigger(reason.trigger)}</p>
                          <p>{reason.message ?? "Resources unavailable during dispatch attempt."}</p>
                          {reason.blocking_resources.length > 0 ? (
                            <p>Blocking resources: <span className="font-medium">{reason.blocking_resources.join(", ")}</span></p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>

                <div className="rounded-2xl bg-slate-50 p-4">
                  <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
                    LLM Explanation
                  </h4>
                  <p className="text-sm text-slate-700">
                    {trace.llm_explanation ?? "No enrichment explanation available for this patient."}
                  </p>
                </div>
              </div>
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

function TraceCell({
  label,
  value,
  strong = false,
  badge,
}: {
  label: string;
  value: string;
  strong?: boolean;
  badge?: string;
}) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</div>
      {badge ? (
        <span className={`mt-1 inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${badge}`}>{value}</span>
      ) : (
        <div className={`mt-1 truncate text-sm ${strong ? "font-semibold text-slate-900" : "text-slate-700"}`}>{value}</div>
      )}
    </div>
  );
}

function formatMinutes(value: number) {
  return `${value.toFixed(2)} min`;
}

function formatOptionalMinutes(value: number | null | undefined) {
  return value === null || value === undefined ? "n/a" : formatMinutes(value);
}

function formatRisk(trace: PatientTrace) {
  const parts = [trace.risk_level ? `L${trace.risk_level}` : null, trace.textual_risk_score ? `T${trace.textual_risk_score}` : null].filter(Boolean);
  return parts.length > 0 ? parts.join(" / ") : "n/a";
}

function formatResourceList(resources: string[]) {
  return resources.length > 0 ? resources.join(", ") : "n/a";
}

function formatTrigger(trigger: string | null | undefined) {
  if (!trigger) return "n/a";
  if (trigger === "arrival_initial_assessment") return "Arrival / initial assessment";
  if (trigger === "service_end_resource_available") return "Service end / resource available";
  if (trigger === "deterioration_reassessment") return "Deterioration reassessment";
  if (trigger === "doctor_round_replan") return "Doctor round replan";
  return trigger;
}

function formatStatusLabel(status: string) {
  if (status === "TREATED") return "Treated";
  if (status === "LEFT_UNTREATED") return "Untreated";
  if (status === "IN_SERVICE") return "In service";
  if (status === "WAITING") return "Waiting";
  return status;
}

function statusStyle(status: string) {
  if (status === "TREATED") return "bg-emerald-100 text-emerald-800";
  if (status === "LEFT_UNTREATED") return "bg-rose-100 text-rose-800";
  if (status === "IN_SERVICE") return "bg-sky-100 text-sky-800";
  return "bg-amber-100 text-amber-800";
}
