import type { ResourceConfigEntry, ResourceSummary } from "../types";
import { formatResourceName } from "../utils/resources";

interface ActiveResourceCatalogPanelProps {
  activeCatalog: Record<string, ResourceConfigEntry>;
  resourceSummary: Record<string, ResourceSummary>;
}

export function ActiveResourceCatalogPanel({
  activeCatalog,
  resourceSummary,
}: ActiveResourceCatalogPanelProps) {
  const resources = Object.values(activeCatalog).sort((left, right) => left.id.localeCompare(right.id));
  if (resources.length === 0) {
    return null;
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-900">Active Resource Catalog</h3>
        <p className="text-sm text-slate-500">
          Effective resource configuration after applying the scenario preset and any advanced overrides.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-600">
            <tr>
              <th className="px-4 py-3 font-medium">Resource</th>
              <th className="px-4 py-3 font-medium">Enabled</th>
              <th className="px-4 py-3 font-medium">Capacity</th>
              <th className="px-4 py-3 font-medium">Utilization</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {resources.map((resource) => {
              const summary = resourceSummary[resource.id];
              const utilization = summary ? `${(summary.average_utilization * 100).toFixed(1)}%` : "n/a";
              return (
                <tr key={resource.id} className="border-t border-slate-100">
                  <td className="px-4 py-3 font-medium text-slate-800">{formatResourceName(resource.id)}</td>
                  <td className="px-4 py-3 text-slate-600">{resource.enabled ? "Enabled" : "Disabled"}</td>
                  <td className="px-4 py-3 text-slate-600">{resource.capacity}</td>
                  <td className="px-4 py-3 text-slate-600">{utilization}</td>
                  <td className="px-4 py-3 text-slate-600">{summary?.status ?? "configured"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
