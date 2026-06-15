import type { SimulationMetrics } from "../types";

interface DoctorRoundPanelProps {
  metrics: SimulationMetrics;
}

export function DoctorRoundPanel({ metrics }: DoctorRoundPanelProps) {
  return (
    <div className="panel p-5">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">Doctor Rounds</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-950">Clinical Review Overhead</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Doctor rounds represent the principal emergency physician reviewing the waiting queue and
          triggering replanning. They consume simulated time.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <RoundStat label="Number of Rounds" value={metrics.number_of_doctor_rounds.toString()} />
        <RoundStat label="Total Round Time" value={`${metrics.total_doctor_round_time.toFixed(2)} min`} />
        <RoundStat
          label="Average Round Duration"
          value={`${metrics.average_doctor_round_duration.toFixed(2)} min`}
        />
        <RoundStat
          label="Planning Overhead"
          value={`${metrics.total_planning_overhead_time.toFixed(2)} min`}
        />
      </div>
    </div>
  );
}

function RoundStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-900">{value}</p>
    </div>
  );
}

