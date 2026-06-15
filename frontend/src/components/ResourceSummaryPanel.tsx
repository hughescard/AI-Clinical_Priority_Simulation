import type { ResourceSummary } from "../types";

interface ResourceSummaryPanelProps {
  resources: Record<string, ResourceSummary>;
}

const statusStyles: Record<string, string> = {
  available: "bg-emerald-100 text-emerald-800 border-emerald-200",
  constrained: "bg-amber-100 text-amber-900 border-amber-200",
  fully_allocated: "bg-rose-100 text-rose-800 border-rose-200",
};

export function ResourceSummaryPanel({ resources }: ResourceSummaryPanelProps) {
  return (
    <div className="panel p-5">
      <div className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">Resource Summary</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-950">Emergency Department Capacity</h3>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Object.entries(resources).map(([resourceName, summary]) => {
          const badgeClass = statusStyles[summary.status] ?? statusStyles.available;
          return (
            <div key={resourceName} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold capitalize text-slate-900">
                    {resourceName.replace(/_/g, " ")}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">Configured capacity: {summary.capacity}</p>
                </div>
                <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${badgeClass}`}>
                  {summary.status.replace(/_/g, " ")}
                </span>
              </div>
              <div className="mt-4 grid gap-2 text-sm text-slate-600">
                <ResourceRow label="Peak in use" value={summary.peak_in_use.toString()} />
                <ResourceRow label="Final in use" value={summary.final_in_use.toString()} />
                <ResourceRow label="Final available" value={summary.final_available.toString()} />
                <ResourceRow label="Avg utilization" value={`${(summary.average_utilization * 100).toFixed(1)}%`} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ResourceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span>{label}</span>
      <span className="font-semibold text-slate-900">{value}</span>
    </div>
  );
}
