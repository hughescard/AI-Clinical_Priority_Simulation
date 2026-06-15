import type { Algorithm } from "../types";
import { formatAlgorithmName } from "../utils/algorithms";

const badgeStyles: Record<Algorithm, string> = {
  fifo: "bg-slate-100 text-slate-800 border-slate-200",
  greedy: "bg-teal-100 text-teal-800 border-teal-200",
  astar: "bg-amber-100 text-amber-900 border-amber-200",
  cpsat: "bg-rose-100 text-rose-900 border-rose-200",
  simulated_annealing: "bg-sky-100 text-sky-900 border-sky-200",
};

interface AlgorithmBadgeProps {
  algorithm: Algorithm;
}

export function AlgorithmBadge({ algorithm }: AlgorithmBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${badgeStyles[algorithm]}`}
    >
      {formatAlgorithmName(algorithm)}
    </span>
  );
}
