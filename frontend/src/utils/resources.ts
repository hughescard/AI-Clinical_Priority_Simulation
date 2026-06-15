import type { AdvancedScenarioConfig, ResourceConfigEntry } from "../types";

export const BASE_RESOURCE_DEFAULTS: ResourceConfigEntry[] = [
  { id: "doctor", capacity: 3, enabled: true },
  { id: "nurse", capacity: 4, enabled: true },
  { id: "observation_bed", capacity: 6, enabled: true },
  { id: "resuscitation_room", capacity: 1, enabled: true },
  { id: "vital_sign_monitor", capacity: 4, enabled: true },
  { id: "laboratory", capacity: 2, enabled: true },
];

export const EXTRA_RESOURCE_DEFAULTS: ResourceConfigEntry[] = [
  { id: "xray_room", capacity: 1, enabled: false },
  { id: "ct_scanner", capacity: 1, enabled: false },
  { id: "ultrasound_room", capacity: 1, enabled: false },
  { id: "isolation_room", capacity: 1, enabled: false },
  { id: "pharmacy", capacity: 1, enabled: false },
  { id: "specialist", capacity: 1, enabled: false },
];

export const ALL_RESOURCE_DEFAULTS = [...BASE_RESOURCE_DEFAULTS, ...EXTRA_RESOURCE_DEFAULTS];

export function formatResourceName(resourceId: string): string {
  return resourceId
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function buildResourceFormState(
  advancedConfig?: AdvancedScenarioConfig | null,
): Record<string, ResourceConfigEntry> {
  const merged = new Map<string, ResourceConfigEntry>();
  for (const resource of ALL_RESOURCE_DEFAULTS) {
    merged.set(resource.id, { ...resource });
  }
  for (const resource of advancedConfig?.resources ?? []) {
    merged.set(resource.id, { ...resource });
  }
  return Object.fromEntries(Array.from(merged.entries()));
}

export function buildAdvancedConfigPayload(
  resources: Record<string, ResourceConfigEntry>,
): AdvancedScenarioConfig | undefined {
  const baseline = new Map(ALL_RESOURCE_DEFAULTS.map((resource) => [resource.id, resource]));
  const changed = Object.values(resources)
    .filter((resource) => {
      const base = baseline.get(resource.id);
      if (!base) {
        return true;
      }
      return base.capacity !== resource.capacity || base.enabled !== resource.enabled;
    })
    .sort((left, right) => left.id.localeCompare(right.id));

  return changed.length > 0 ? { resources: changed } : undefined;
}
