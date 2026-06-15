type DashboardTab = "simulation" | "experiments";

interface SectionTabsProps {
  activeTab: DashboardTab;
  onChange: (tab: DashboardTab) => void;
}

const tabConfig: Array<{ key: DashboardTab; label: string; description: string }> = [
  {
    key: "simulation",
    label: "Single Simulation",
    description: "Inspect one ER run with timeline and operational metrics.",
  },
  {
    key: "experiments",
    label: "Experiment Comparison",
    description: "Compare algorithms across repeated seeded replications.",
  },
];

export function SectionTabs({ activeTab, onChange }: SectionTabsProps) {
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {tabConfig.map((tab) => {
        const isActive = tab.key === activeTab;
        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChange(tab.key)}
            className={`rounded-[1.75rem] border px-5 py-4 text-left transition ${
              isActive
                ? "border-emerald-300 bg-emerald-50 shadow-[0_14px_28px_rgba(5,150,105,0.12)]"
                : "border-slate-200 bg-white hover:border-slate-300"
            }`}
          >
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">{tab.label}</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">{tab.description}</p>
          </button>
        );
      })}
    </div>
  );
}
