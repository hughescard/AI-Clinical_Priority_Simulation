import type { PropsWithChildren, ReactNode } from "react";

interface LayoutProps extends PropsWithChildren {
  status: ReactNode;
}

export function Layout({ status, children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(22,163,74,0.12),_transparent_28%),linear-gradient(180deg,_#f7fbfc_0%,_#eef4f7_100%)] text-slate-900">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 rounded-[2rem] border border-white/70 bg-white/85 px-6 py-8 shadow-[0_18px_60px_rgba(15,23,42,0.08)] backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.26em] text-emerald-700">
                Emergency Operations Dashboard
              </p>
              <h1 className="text-4xl font-semibold tracking-tight text-slate-950">
                Clinical Triage Simulator
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
                Discrete-event emergency room simulation with LLM enrichment and AI planning
                algorithms.
              </p>
            </div>
            <div>{status}</div>
          </div>
        </header>
        <main className="space-y-8">{children}</main>
      </div>
    </div>
  );
}

