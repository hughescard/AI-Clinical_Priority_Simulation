export function AlgorithmGuide() {
  return (
    <div className="panel p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">Algorithm Guide</p>
      <h3 className="mt-2 text-xl font-semibold text-slate-950">Planning Strategies</h3>
      <div className="mt-4 grid gap-3">
        <GuideRow
          title="FIFO"
          description="Arrival-order baseline. Serves patients in chronological queue order."
        />
        <GuideRow
          title="Greedy"
          description="Immediate priority heuristic. Emphasizes current urgency, waiting time, and deterioration."
        />
        <GuideRow
          title="A*"
          description="Informed search over a bounded planning window. Balances urgency, delay, duration, and resource feasibility."
        />
        <GuideRow
          title="CP-SAT"
          description="Constraint optimization planner using OR-Tools to select a feasible high-utility batch under resource constraints."
        />
      </div>
    </div>
  );
}

function GuideRow({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
      <p className="font-semibold text-slate-900">{title}</p>
      <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
    </div>
  );
}
