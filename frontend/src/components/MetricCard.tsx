interface MetricCardProps {
  label: string;
  value: string | number;
  accent?: "default" | "danger" | "success" | "warning";
}

const accentStyles = {
  default: "border-slate-200 bg-white",
  danger: "border-rose-200 bg-rose-50",
  success: "border-emerald-200 bg-emerald-50",
  warning: "border-amber-200 bg-amber-50",
};

export function MetricCard({ label, value, accent = "default" }: MetricCardProps) {
  return (
    <div className={`rounded-2xl border p-4 shadow-sm ${accentStyles[accent]}`}>
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
    </div>
  );
}

