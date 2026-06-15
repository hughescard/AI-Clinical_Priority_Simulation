import type { ResourceConfigEntry } from "../types";
import { BASE_RESOURCE_DEFAULTS, EXTRA_RESOURCE_DEFAULTS, formatResourceName } from "../utils/resources";

interface AdvancedConfigPanelProps {
  expanded: boolean;
  onToggle: () => void;
  resources: Record<string, ResourceConfigEntry>;
  onChange: (resourceId: string, updates: Partial<ResourceConfigEntry>) => void;
}

export function AdvancedConfigPanel({
  expanded,
  onToggle,
  resources,
  onChange,
}: AdvancedConfigPanelProps) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between text-left"
      >
        <div>
          <p className="text-sm font-semibold text-slate-900">Advanced Scenario Configuration</p>
          <p className="text-xs text-slate-500">
            Override resource capacities, disable baseline resources, and enable optional equipment.
          </p>
        </div>
        <span className="text-lg text-slate-500">{expanded ? "▾" : "▸"}</span>
      </button>

      {expanded ? (
        <div className="mt-4 space-y-5">
          <ResourceTable
            title="Core Resources"
            resources={BASE_RESOURCE_DEFAULTS.map((resource) => resources[resource.id] ?? resource)}
            onChange={onChange}
          />
          <ResourceTable
            title="Optional Resources"
            resources={EXTRA_RESOURCE_DEFAULTS.map((resource) => resources[resource.id] ?? resource)}
            onChange={onChange}
          />
        </div>
      ) : null}
    </div>
  );
}

interface ResourceTableProps {
  title: string;
  resources: ResourceConfigEntry[];
  onChange: (resourceId: string, updates: Partial<ResourceConfigEntry>) => void;
}

function ResourceTable({ title, resources, onChange }: ResourceTableProps) {
  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-slate-900">{title}</h4>
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-600">
            <tr>
              <th className="px-4 py-3 font-medium">Resource</th>
              <th className="px-4 py-3 font-medium">Enabled</th>
              <th className="px-4 py-3 font-medium">Capacity</th>
            </tr>
          </thead>
          <tbody>
            {resources.map((resource) => (
              <tr key={resource.id} className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-800">{formatResourceName(resource.id)}</td>
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={resource.enabled}
                    onChange={(event) => onChange(resource.id, { enabled: event.target.checked })}
                    className="h-4 w-4 accent-emerald-600"
                  />
                </td>
                <td className="px-4 py-3">
                  <input
                    type="number"
                    min={0}
                    value={resource.capacity}
                    onChange={(event) => onChange(resource.id, { capacity: Number(event.target.value) })}
                    className="field-input max-w-28"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
