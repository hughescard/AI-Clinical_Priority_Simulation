import { useMemo, useState } from "react";

import type { TimelineEvent } from "../types";
import { formatAlgorithmName } from "../utils/algorithms";

interface TimelineProps {
  events: TimelineEvent[];
}

export function Timeline({ events }: TimelineProps) {
  const [eventTypeFilter, setEventTypeFilter] = useState<
    "all" | "patient_arrivals" | "initial_assessments" | "service_starts" | "service_ends" | "deterioration_updates" | "doctor_rounds" | "dispatch_attempts"
  >("all");
  const [patientFilter, setPatientFilter] = useState<string>("all");
  const [triggerFilter, setTriggerFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const patientOptions = useMemo(
    () =>
      Array.from(new Set(events.map((event) => event.patient_id).filter((patientId): patientId is string => Boolean(patientId)))).sort(),
    [events],
  );

  const triggerOptions = useMemo(
    () =>
      Array.from(new Set(events.map((event) => event.trigger).filter((trigger): trigger is string => Boolean(trigger)))).sort(),
    [events],
  );

  const visibleEvents = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return events.filter((event) => {
      if (!matchesEventTypeFilter(event, eventTypeFilter)) {
        return false;
      }
      if (patientFilter !== "all" && event.patient_id !== patientFilter) {
        return false;
      }
      if (triggerFilter !== "all" && event.trigger !== triggerFilter) {
        return false;
      }
      if (!normalizedSearch) {
        return true;
      }
      return buildSearchableEventText(event).includes(normalizedSearch);
    });
  }, [eventTypeFilter, events, patientFilter, search, triggerFilter]);

  const visibleCounts = useMemo(() => {
    return {
      serviceStarts: visibleEvents.filter((event) => event.event_type === "SERVICE_START").length,
      dispatchAttempts: visibleEvents.filter((event) => event.event_type === "DISPATCH_ATTEMPT").length,
      deteriorationEvents: visibleEvents.filter((event) => event.event_type === "DETERIORATION_UPDATE").length,
      doctorRounds: visibleEvents.filter((event) =>
        event.event_type === "DOCTOR_ROUND_START" ||
        event.event_type === "DOCTOR_ROUND_END" ||
        event.event_type === "DOCTOR_ROUND_IDLE_CHECK",
      ).length,
    };
  }, [visibleEvents]);

  return (
    <div className="rounded-3xl border border-slate-200 bg-slate-950 p-4 text-slate-100 shadow-[0_20px_45px_rgba(15,23,42,0.22)]">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">Timeline</h3>
          <p className="text-sm text-slate-400">Chronological simulation events with filtering for long runs.</p>
        </div>
        <span className="rounded-full border border-slate-700 px-3 py-1 text-xs font-medium text-slate-300">
          {visibleEvents.length} / {events.length} events
        </span>
      </div>
      <div className="mb-4 grid gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 lg:grid-cols-4">
        <label className="flex flex-col gap-2 text-sm text-slate-300">
          Event Type
          <select
            value={eventTypeFilter}
            onChange={(event) => setEventTypeFilter(event.target.value as typeof eventTypeFilter)}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
          >
            <option value="all">All events</option>
            <option value="patient_arrivals">Patient arrivals</option>
            <option value="initial_assessments">Initial assessments</option>
            <option value="service_starts">Service starts</option>
            <option value="service_ends">Service ends</option>
            <option value="deterioration_updates">Deterioration updates</option>
            <option value="doctor_rounds">Doctor rounds</option>
            <option value="dispatch_attempts">Dispatch attempts</option>
          </select>
        </label>

        <label className="flex flex-col gap-2 text-sm text-slate-300">
          Patient
          <select
            value={patientFilter}
            onChange={(event) => setPatientFilter(event.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
          >
            <option value="all">All patients</option>
            {patientOptions.map((patientId) => (
              <option key={patientId} value={patientId}>
                {patientId}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-2 text-sm text-slate-300">
          Trigger
          <select
            value={triggerFilter}
            onChange={(event) => setTriggerFilter(event.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
          >
            <option value="all">All triggers</option>
            {triggerOptions.map((trigger) => (
              <option key={trigger} value={trigger}>
                {formatTrigger(trigger)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-2 text-sm text-slate-300">
          Search
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Patient, event, trigger, category..."
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
          />
        </label>
      </div>

      <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <SummaryChip label="Total events" value={events.length} />
        <SummaryChip label="Visible events" value={visibleEvents.length} />
        <SummaryChip label="Service starts" value={visibleCounts.serviceStarts} />
        <SummaryChip label="Dispatch attempts" value={visibleCounts.dispatchAttempts} />
        <SummaryChip label="Deterioration events" value={visibleCounts.deteriorationEvents} />
        <SummaryChip label="Doctor rounds" value={visibleCounts.doctorRounds} />
      </div>
      <div className="max-h-[28rem] overflow-y-auto rounded-2xl border border-slate-800">
        <ul className="divide-y divide-slate-800">
          {visibleEvents.map((event, index) => (
            <li key={`${event.event_type}-${event.time}-${event.patient_id ?? "none"}-${index}`} className="grid gap-2 px-4 py-3 sm:grid-cols-[7rem_1fr]">
              <div className="text-sm font-semibold text-emerald-300">t = {event.time.toFixed(2)}</div>
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <EventBadge eventType={event.event_type} />
                  {event.patient_id ? (
                    <>
                      <span className="text-xs text-slate-400">Patient: {event.patient_id}</span>
                      <a
                        href={`#patient-trace-${event.patient_id}`}
                        className="text-xs font-medium text-emerald-300 underline-offset-2 hover:underline"
                      >
                        View trace
                      </a>
                    </>
                  ) : null}
                  {event.algorithm ? (
                    <span className="text-xs text-slate-400">Algorithm: {formatAlgorithmName(event.algorithm)}</span>
                  ) : null}
                  {event.critical_waiting ? <InlineBadge label="Critical waiting" tone="rose" /> : null}
                  {event.event_type === "DETERIORATION_UPDATE" && event.priority_changes && event.priority_changes.length > 0 ? (
                    <InlineBadge label="Deteriorated while waiting" tone="amber" />
                  ) : null}
                  {event.event_type === "DISPATCH_ATTEMPT" && event.blocking_resources && event.blocking_resources.length > 0 ? (
                    <InlineBadge label="Dispatch blocked" tone="orange" />
                  ) : null}
                  {event.event_type === "SERVICE_START" ? <InlineBadge label="Service started" tone="emerald" /> : null}
                  {event.trigger === "doctor_round_replan" ? <InlineBadge label="Doctor round replan" tone="fuchsia" /> : null}
                </div>
                {isDoctorRoundEvent(event) ? (
                  <p className="text-sm text-slate-200">
                    Doctor round review with <span className="font-medium">{event.waiting_patient_count ?? 0}</span> waiting patients and{" "}
                    <span className="font-medium">{event.active_service_count ?? event.active_patient_count ?? 0}</span> active services.
                  </p>
                ) : null}
                {event.event_type === "DISPATCH_ATTEMPT" ? (
                  <p className="text-sm text-slate-200">
                    Dispatch attempt checked <span className="font-medium">{event.waiting_patient_count ?? 0}</span> waiting patients and could start{" "}
                    <span className="font-medium">{event.started_patient_count ?? 0}</span>.
                  </p>
                ) : null}
                {event.waiting_patient_count !== undefined ? (
                  <p className="text-sm text-slate-300">
                    Waiting patients: <span className="font-medium">{event.waiting_patient_count}</span>
                  </p>
                ) : null}
                {event.active_patient_count !== undefined ? (
                  <p className="text-sm text-slate-300">
                    Active services: <span className="font-medium">{event.active_patient_count}</span>
                  </p>
                ) : null}
                {event.active_patient_count === undefined && event.active_service_count !== undefined ? (
                  <p className="text-sm text-slate-300">
                    Active services: <span className="font-medium">{event.active_service_count}</span>
                  </p>
                ) : null}
                {event.trigger ? (
                  <p className="text-sm text-slate-300">
                    Trigger: <span className="font-medium">{formatTrigger(event.trigger)}</span>
                  </p>
                ) : null}
                {event.feasible_patient_count !== undefined ? (
                  <p className="text-sm text-slate-300">
                    Feasible patients: <span className="font-medium">{event.feasible_patient_count}</span>
                  </p>
                ) : null}
                {event.started_patient_count !== undefined ? (
                  <p className="text-sm text-slate-300">
                    Started patients: <span className="font-medium">{event.started_patient_count}</span>
                  </p>
                ) : null}
                {event.blocking_resources && event.blocking_resources.length > 0 ? (
                  <p className="text-sm text-slate-300">
                    Blocking resources: <span className="font-medium">{event.blocking_resources.join(", ")}</span>
                  </p>
                ) : null}
                {event.clinical_category ? (
                  <p className="text-sm text-slate-300">
                    Clinical category: <span className="font-medium">{event.clinical_category}</span>
                  </p>
                ) : null}
                {event.required_resources && event.required_resources.length > 0 ? (
                  <p className="text-sm text-slate-300">
                    Required resources: <span className="font-medium">{event.required_resources.join(", ")}</span>
                  </p>
                ) : null}
                {event.resources_allocated && event.resources_allocated.length > 0 ? (
                  <p className="text-sm text-slate-300">
                    Resources allocated: <span className="font-medium">{event.resources_allocated.join(", ")}</span>
                  </p>
                ) : null}
                {event.resources_released && event.resources_released.length > 0 ? (
                  <p className="text-sm text-slate-300">
                    Resources released: <span className="font-medium">{event.resources_released.join(", ")}</span>
                  </p>
                ) : null}
                {event.selected_for_immediate_service !== undefined ? (
                  <p className="text-sm text-slate-300">
                    Immediate service:{" "}
                    <span className="font-medium">{event.selected_for_immediate_service ? "yes" : "no"}</span>
                  </p>
                ) : null}
                {event.critical_waiting ? (
                  <p className="text-sm text-rose-300">Critical case is still waiting for resources.</p>
                ) : null}
                {event.affected_waiting_patients !== undefined ? (
                  <p className="text-sm text-slate-300">
                    Affected waiting patients: <span className="font-medium">{event.affected_waiting_patients}</span>
                  </p>
                ) : null}
                {event.priority_changes && event.priority_changes.length > 0 ? (
                  <p className="text-sm text-slate-300">
                    Priority changes: <span className="font-medium">{event.priority_changes.join(", ")}</span>
                  </p>
                ) : null}
                {event.round_duration !== undefined ? (
                  <p className="text-sm text-slate-300">
                    Round duration: <span className="font-medium">{event.round_duration.toFixed(2)} min</span>
                  </p>
                ) : null}
                {event.planning_overhead !== undefined ? (
                  <p className="text-sm text-slate-300">
                    Planning overhead:{" "}
                    <span className="font-medium">{event.planning_overhead.toFixed(2)} min</span>
                  </p>
                ) : null}
                {event.message ? <p className="text-sm text-slate-400">{event.message}</p> : null}
                {event.note ? <p className="text-sm text-slate-400">{event.note}</p> : null}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function SummaryChip({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-3">
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className="mt-1 text-lg font-semibold text-slate-100">{value}</div>
    </div>
  );
}

function InlineBadge({ label, tone }: { label: string; tone: "rose" | "amber" | "orange" | "emerald" | "fuchsia" }) {
  const styles = {
    rose: "bg-rose-900/70 text-rose-100",
    amber: "bg-amber-900/70 text-amber-100",
    orange: "bg-orange-900/70 text-orange-100",
    emerald: "bg-emerald-900/70 text-emerald-100",
    fuchsia: "bg-fuchsia-900/70 text-fuchsia-100",
  };
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${styles[tone]}`}>{label}</span>;
}

function matchesEventTypeFilter(
  event: TimelineEvent,
  filter:
    | "all"
    | "patient_arrivals"
    | "initial_assessments"
    | "service_starts"
    | "service_ends"
    | "deterioration_updates"
    | "doctor_rounds"
    | "dispatch_attempts",
) {
  if (filter === "all") return true;
  if (filter === "patient_arrivals") return event.event_type === "PATIENT_ARRIVAL";
  if (filter === "initial_assessments") return event.event_type === "INITIAL_ASSESSMENT";
  if (filter === "service_starts") return event.event_type === "SERVICE_START";
  if (filter === "service_ends") return event.event_type === "SERVICE_END";
  if (filter === "deterioration_updates") return event.event_type === "DETERIORATION_UPDATE";
  if (filter === "doctor_rounds") {
    return (
      event.event_type === "DOCTOR_ROUND_START" ||
      event.event_type === "DOCTOR_ROUND_END" ||
      event.event_type === "DOCTOR_ROUND_IDLE_CHECK"
    );
  }
  return event.event_type === "DISPATCH_ATTEMPT";
}

function buildSearchableEventText(event: TimelineEvent) {
  return [
    event.patient_id,
    event.event_type,
    event.algorithm ? formatAlgorithmName(event.algorithm) : null,
    event.clinical_category,
    event.trigger,
    event.blocking_resources?.join(" "),
    event.message,
    event.note,
    event.priority_changes?.join(" "),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function formatTrigger(trigger: string | null | undefined) {
  if (!trigger) return "n/a";
  if (trigger === "arrival_initial_assessment") return "Arrival / initial assessment";
  if (trigger === "service_end_resource_available") return "Service end / resource available";
  if (trigger === "deterioration_reassessment") return "Deterioration reassessment";
  if (trigger === "doctor_round_replan") return "Doctor round replan";
  return trigger;
}

function isDoctorRoundEvent(event: TimelineEvent) {
  return (
    event.event_type === "DOCTOR_ROUND_START" ||
    event.event_type === "DOCTOR_ROUND_END" ||
    event.event_type === "DOCTOR_ROUND_IDLE_CHECK"
  );
}

function EventBadge({ eventType }: { eventType: string }) {
  const styles: Record<string, string> = {
    PATIENT_ARRIVAL: "bg-sky-900/70 text-sky-100",
    INITIAL_ASSESSMENT: "bg-cyan-900/70 text-cyan-100",
    DISPATCH_ATTEMPT: "bg-orange-900/70 text-orange-100",
    SERVICE_START: "bg-emerald-900/70 text-emerald-100",
    SERVICE_END: "bg-indigo-900/70 text-indigo-100",
    DETERIORATION_UPDATE: "bg-amber-900/70 text-amber-100",
    DOCTOR_ROUND_START: "bg-rose-900/70 text-rose-100",
    DOCTOR_ROUND_END: "bg-fuchsia-900/70 text-fuchsia-100",
    DOCTOR_ROUND_IDLE_CHECK: "bg-slate-700 text-slate-100",
  };
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${styles[eventType] ?? "bg-slate-800 text-slate-100"}`}>
      {eventType}
    </span>
  );
}
