import { useState } from "react";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type {
  Algorithm,
  ExperimentAnalysis,
  ExperimentComparisonRequest,
  ExperimentComparisonResponse,
  ExperimentMetricKey,
  MetricSummary,
} from "../types";
import { formatAlgorithmName } from "../utils/algorithms";

const chartColors: Record<Algorithm, string> = {
  fifo: "#475569",
  greedy: "#0f766e",
  astar: "#b45309",
  cpsat: "#be123c",
  simulated_annealing: "#0369a1",
};

const CLINICAL_CHART_METRICS: ExperimentMetricKey[] = [
  "critical_late_patients",
  "total_clinical_impact",
  "untreated_patients",
  "patients_deteriorated_while_waiting",
  "critical_patients_waited",
  "critical_patients_started_immediately",
];

const OPERATIONAL_CHART_METRICS: ExperimentMetricKey[] = [
  "average_waiting_time",
  "average_time_to_service_start",
  "average_resource_utilization",
  "max_waiting_time",
  "treated_patients",
  "services_started_from_arrival",
  "services_started_from_service_end",
];

const COMPUTATIONAL_CHART_METRICS: ExperimentMetricKey[] = [
  "total_planning_overhead_time",
];

const DEFAULT_VISIBLE_CATEGORY_CHARTS = 3;

interface ExperimentResultsProps {
  result: ExperimentComparisonResponse;
  analysis: ExperimentAnalysis | null;
  request: ExperimentComparisonRequest;
  onDownloadJson: (payload: ExperimentComparisonRequest) => Promise<void>;
  onDownloadCsv: (payload: ExperimentComparisonRequest) => Promise<void>;
  onDownloadSummaryCsv: (payload: ExperimentComparisonRequest) => Promise<void>;
  exportError: string | null;
}

function buildChartData(result: ExperimentComparisonResponse, metric: keyof ExperimentComparisonResponse["results"][Algorithm]) {
  return result.algorithms.map((algorithm) => ({
    algorithm,
    value: result.results[algorithm][metric].mean,
  }));
}

export function ExperimentResults({
  result,
  analysis,
  request,
  onDownloadJson,
  onDownloadCsv,
  onDownloadSummaryCsv,
  exportError,
}: ExperimentResultsProps) {
  const [showMoreClinical, setShowMoreClinical] = useState(false);
  const [showMoreOperational, setShowMoreOperational] = useState(false);
  const comparisonMetrics: Array<{ key: ExperimentMetricKey; label: string; better: "lower" | "higher" }> = [
    { key: "average_waiting_time", label: "Average Waiting Time", better: "lower" },
    { key: "critical_late_patients", label: "Critical Late Patients", better: "lower" },
    { key: "total_clinical_impact", label: "Total Clinical Impact", better: "lower" },
    { key: "average_resource_utilization", label: "Average Resource Utilization", better: "higher" },
    { key: "total_planning_overhead_time", label: "Total Planning Overhead", better: "lower" },
  ];

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
        <p className="text-sm text-slate-700">
          Use exported JSON/CSV files to reproduce tables and figures in the final report.
        </p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="action-button" onClick={() => void onDownloadJson(request)}>
            Download JSON
          </button>
          <button type="button" className="action-button" onClick={() => void onDownloadCsv(request)}>
            Download CSV
          </button>
          <button type="button" className="action-button" onClick={() => void onDownloadSummaryCsv(request)}>
            Download Summary CSV
          </button>
        </div>
      </div>
      {exportError ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {exportError}
        </div>
      ) : null}
      <div className="panel p-5">
        <div className="mb-4 flex flex-wrap gap-3 text-sm text-slate-600">
          <span>Scenario: {result.scenario}</span>
          <span>Seed start: {result.seed_start}</span>
          <span>Replications: {result.replications}</span>
          <span>Duration: {result.duration_minutes} min</span>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-2 text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-[0.18em] text-slate-500">
                <th className="pr-4">Metric</th>
                {result.algorithms.map((algorithm) => (
                  <th key={algorithm} className="pr-4">
                    {formatAlgorithmName(algorithm)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparisonMetrics.map((metric) => {
                const bestAlgorithms = findBestAlgorithms(result, metric.key, metric.better);
                return (
                  <tr key={metric.key} className="text-slate-800">
                    <td className="rounded-l-2xl bg-slate-50 px-4 py-3 font-semibold">{metric.label}</td>
                    {result.algorithms.map((algorithm, index) => {
                      const summary = result.results[algorithm][metric.key];
                      const isBest = bestAlgorithms.includes(algorithm);
                      return (
                        <td
                          key={`${metric.key}-${algorithm}`}
                          className={`px-4 py-3 ${index === result.algorithms.length - 1 ? "rounded-r-2xl" : ""} ${
                            isBest ? "bg-emerald-50" : "bg-white"
                          }`}
                        >
                          <MetricSummaryCell
                            summary={summary}
                            emphasize={isBest}
                            metricKey={metric.key}
                          />
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      {analysis ? <RankingAnalysisPanel analysis={analysis} /> : null}
      {analysis ? (
        <VisualComparisonDashboard
          result={result}
          analysis={analysis}
          showMoreClinical={showMoreClinical}
          showMoreOperational={showMoreOperational}
          onToggleClinical={() => setShowMoreClinical((current) => !current)}
          onToggleOperational={() => setShowMoreOperational((current) => !current)}
        />
      ) : null}
    </section>
  );
}

interface VisualComparisonDashboardProps {
  result: ExperimentComparisonResponse;
  analysis: ExperimentAnalysis;
  showMoreClinical: boolean;
  showMoreOperational: boolean;
  onToggleClinical: () => void;
  onToggleOperational: () => void;
}

function VisualComparisonDashboard({
  result,
  analysis,
  showMoreClinical,
  showMoreOperational,
  onToggleClinical,
  onToggleOperational,
}: VisualComparisonDashboardProps) {
  const clinicalMetrics = showMoreClinical
    ? CLINICAL_CHART_METRICS
    : CLINICAL_CHART_METRICS.slice(0, DEFAULT_VISIBLE_CATEGORY_CHARTS);
  const operationalMetrics = showMoreOperational
    ? OPERATIONAL_CHART_METRICS
    : OPERATIONAL_CHART_METRICS.slice(0, DEFAULT_VISIBLE_CATEGORY_CHARTS);

  return (
    <section className="space-y-6">
      <div className="panel p-5">
        <h3 className="text-xl font-semibold text-slate-950">Visual Algorithm Comparison</h3>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          Charts are grouped by analysis category so each metric has one clear primary visualization.
        </p>
      </div>

      <ChartSection
        title="Clinical Performance"
        description="Clinical metrics prioritize patient outcomes and late-critical care reduction."
        metrics={clinicalMetrics}
        result={result}
        analysis={analysis}
        onToggleMore={CLINICAL_CHART_METRICS.length > DEFAULT_VISIBLE_CATEGORY_CHARTS ? onToggleClinical : undefined}
        showMore={showMoreClinical}
        canShowMore={CLINICAL_CHART_METRICS.length > DEFAULT_VISIBLE_CATEGORY_CHARTS}
      />

      <ChartSection
        title="Operational Efficiency"
        description="Operational metrics measure flow, waiting time, service start speed, and resource use."
        metrics={operationalMetrics}
        result={result}
        analysis={analysis}
        onToggleMore={
          OPERATIONAL_CHART_METRICS.length > DEFAULT_VISIBLE_CATEGORY_CHARTS ? onToggleOperational : undefined
        }
        showMore={showMoreOperational}
        canShowMore={OPERATIONAL_CHART_METRICS.length > DEFAULT_VISIBLE_CATEGORY_CHARTS}
      />

      <ChartSection
        title="Computational Cost"
        description="Computational cost captures the simulated planning overhead introduced by each algorithm."
        metrics={COMPUTATIONAL_CHART_METRICS}
        result={result}
        analysis={analysis}
      />

      <BalancedRankingSection analysis={analysis} />
    </section>
  );
}

interface ChartSectionProps {
  title: string;
  description: string;
  metrics: ExperimentMetricKey[];
  result: ExperimentComparisonResponse;
  analysis: ExperimentAnalysis;
  showMore?: boolean;
  canShowMore?: boolean;
  onToggleMore?: () => void;
}

function ChartSection({
  title,
  description,
  metrics,
  result,
  analysis,
  showMore = false,
  canShowMore = false,
  onToggleMore,
}: ChartSectionProps) {
  return (
    <div className="panel p-5">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-xl font-semibold text-slate-950">{title}</h3>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">{description}</p>
        </div>
        {canShowMore && onToggleMore ? (
          <button type="button" className="action-button" onClick={onToggleMore}>
            {showMore ? "Show Fewer Metrics" : "Show More Metrics"}
          </button>
        ) : null}
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        {metrics.map((metric) => (
          <MetricBarChart
            key={`${title}-${metric}`}
            metric={metric}
            result={result}
            analysis={analysis}
          />
        ))}
      </div>
    </div>
  );
}

function MetricBarChart({
  metric,
  result,
  analysis,
}: {
  metric: ExperimentMetricKey;
  result: ExperimentComparisonResponse;
  analysis: ExperimentAnalysis;
}) {
  const ranking = analysis.per_metric_rankings.find((row) => row.metric_name === metric);
  const winnerAlgorithms = new Set(
    ranking?.ranking.filter((row) => row.rank === 1).map((row) => row.algorithm as Algorithm) ?? [],
  );
  const data = result.algorithms.map((algorithm) => ({
    algorithm,
    label: formatAlgorithmName(algorithm),
    value: result.results[algorithm][metric].mean,
    std: result.results[algorithm][metric].std,
    winner: winnerAlgorithms.has(algorithm),
  }));
  const isTie = winnerAlgorithms.size > 1;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="text-base font-semibold text-slate-900">{metricDisplayLabel(metric)}</h4>
          <p className="mt-1 text-sm text-slate-600">{formatDirection(metricDirectionFromAnalysis(metric, analysis))}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {[...winnerAlgorithms].map((algorithm) => (
            <span
              key={`${metric}-${algorithm}`}
              className={`rounded-full px-2.5 py-1 text-xs font-semibold ${algorithmBadgeStyle(algorithm)}`}
            >
              {formatAlgorithmName(algorithm)}
            </span>
          ))}
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
              isTie ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-800"
            }`}
          >
            {isTie ? "Practical tie at rank 1" : "Best mean"}
          </span>
        </div>
      </div>

      <div className="h-[18rem]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ea" />
            <XAxis dataKey="label" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip
              formatter={(value: number) => formatMetricValue(metric, value)}
              labelFormatter={(value) => `Algorithm: ${String(value)}`}
            />
            <Bar dataKey="value" radius={[10, 10, 0, 0]}>
              {data.map((entry) => (
                <Cell
                  key={`${metric}-${entry.algorithm}`}
                  fill={chartColors[entry.algorithm]}
                  fillOpacity={entry.winner ? 1 : 0.72}
                  stroke={entry.winner ? "#0f172a" : "transparent"}
                  strokeWidth={entry.winner ? 2 : 0}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
        {data.map((entry) => (
          <span key={`${metric}-summary-${entry.algorithm}`}>
            {formatAlgorithmName(entry.algorithm)} mean {formatMetricValue(metric, entry.value)} · std{" "}
            {formatMetricValue(metric, entry.std)}
          </span>
        ))}
      </div>
    </div>
  );
}

function BalancedRankingSection({ analysis }: { analysis: ExperimentAnalysis }) {
  const data = analysis.balanced_overall_ranking.map((row) => ({
    algorithm: row.algorithm as Algorithm,
    label: formatAlgorithmName(row.algorithm),
    value: row.balanced_score,
    clinical: row.clinical_score,
    operational: row.operational_score,
    computational: row.computational_score,
  }));

  return (
    <div className="panel p-5">
      <div className="mb-5">
        <h3 className="text-xl font-semibold text-slate-950">Balanced Ranking</h3>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          Balanced ranking combines clinical, operational, and computational dimensions with clinical performance weighted highest.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="h-[20rem]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ left: 12, right: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ea" />
              <XAxis type="number" stroke="#64748b" domain={[0, 1]} />
              <YAxis dataKey="label" type="category" stroke="#64748b" width={90} />
              <Tooltip
                formatter={(value: number, name) => {
                  if (name === "Balanced Score") return value.toFixed(3);
                  return value.toFixed(3);
                }}
              />
              <Bar dataKey="value" name="Balanced Score" radius={[0, 10, 10, 0]}>
                {data.map((entry, index) => (
                  <Cell
                    key={`balanced-${entry.algorithm}`}
                    fill={chartColors[entry.algorithm]}
                    fillOpacity={index === 0 ? 1 : 0.78}
                    stroke={index === 0 ? "#0f172a" : "transparent"}
                    strokeWidth={index === 0 ? 2 : 0}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {analysis.balanced_overall_ranking.map((row) => (
            <div key={`balanced-breakdown-${row.algorithm}`} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm">
              <div className="font-semibold text-slate-900">{formatAlgorithmName(row.algorithm)}</div>
              <div className="mt-1 text-slate-600">Balanced: {row.balanced_score.toFixed(3)}</div>
              <div className="text-slate-600">Clinical: {row.clinical_score.toFixed(3)}</div>
              <div className="text-slate-600">Operational: {row.operational_score.toFixed(3)}</div>
              <div className="text-slate-600">Computational: {row.computational_score.toFixed(3)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RankingAnalysisPanel({ analysis }: { analysis: ExperimentAnalysis }) {
  const keyMetrics = new Set([
    "critical_late_patients",
    "total_clinical_impact",
    "average_waiting_time",
    "untreated_patients",
    "average_time_to_service_start",
    "treated_patients",
    "average_resource_utilization",
    "total_planning_overhead_time",
  ]);
  const rankingRows = analysis.per_metric_rankings.filter((row) => keyMetrics.has(row.metric_name));
  const comparisonRows = analysis.baseline_analysis.comparisons_vs_baseline.filter((row) =>
    keyMetrics.has(row.metric_name),
  );

  return (
    <div className="panel p-5">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h3 className="text-xl font-semibold text-slate-950">Algorithm Ranking &amp; Baseline Analysis</h3>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
          Ranking-first analysis
        </span>
        {analysis.baseline_analysis.available ? (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
            Baseline: {formatAlgorithmName(analysis.baseline_analysis.baseline_algorithm)}
          </span>
        ) : null}
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 p-4">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
            Balanced Overall Ranking
          </h4>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-[0.16em] text-slate-500">
                  <th className="pb-2 pr-3">Rank</th>
                  <th className="pb-2 pr-3">Algorithm</th>
                  <th className="pb-2 pr-3">Balanced</th>
                  <th className="pb-2 pr-3">Clinical</th>
                  <th className="pb-2 pr-3">Operational</th>
                  <th className="pb-2">Computational</th>
                </tr>
              </thead>
              <tbody>
                {analysis.overall_ranking.map((row) => (
                  <tr key={row.algorithm} className="border-t border-slate-100">
                    <td className="py-2 pr-3 font-semibold text-slate-900">#{row.rank}</td>
                    <td className="py-2 pr-3 text-slate-700">{formatAlgorithmName(row.algorithm)}</td>
                    <td className="py-2 pr-3 text-slate-700">{row.balanced_score.toFixed(3)}</td>
                    <td className="py-2 pr-3 text-slate-700">{row.clinical_score.toFixed(3)}</td>
                    <td className="py-2 pr-3 text-slate-700">{row.operational_score.toFixed(3)}</td>
                    <td className="py-2 text-slate-700">{row.computational_score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 p-4">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
            Headline Findings
          </h4>
          <div className="space-y-3 text-sm text-slate-700">
            {analysis.headline_findings.map((finding) => (
              <p key={finding} className="rounded-2xl bg-slate-50 px-4 py-3">
                {finding}
              </p>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-3">
        <CategoryRankingPanel title="Clinical Ranking" ranking={analysis.clinical_ranking} />
        <CategoryRankingPanel title="Operational Ranking" ranking={analysis.operational_ranking} />
        <CategoryRankingPanel title="Computational Cost Ranking" ranking={analysis.computational_ranking} />
      </div>

      <div className="mt-5 rounded-2xl border border-slate-200 p-4">
        <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
          Key Metric Winners
        </h4>
        <p className="mb-4 text-sm text-slate-600">
          Each property is shown as its own block so the ranking for one metric stays visually separate from the next.
        </p>
        <div className="space-y-4">
          {rankingRows.map((row, index) => {
            const topRank = row.ranking[0]?.rank ?? 1;
            const leaders = row.ranking.filter((entry) => entry.rank === topRank);
            const leaderCount = leaders.length;
            return (
              <details
                key={row.metric_name}
                open={index === 0}
                className="group rounded-2xl border border-slate-200 bg-white"
              >
                <summary className="flex cursor-pointer list-none flex-wrap items-start justify-between gap-3 p-4">
                  <div>
                    <h5 className="text-base font-semibold text-slate-900">{row.display_label}</h5>
                    <p className="mt-1 text-sm text-slate-600">{formatDirection(row.direction)}</p>
                  </div>
                  <div className="flex flex-wrap items-center justify-end gap-2">
                    {leaders.map((entry) => (
                      <span
                        key={`${row.metric_name}-${entry.algorithm}`}
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${algorithmBadgeStyle(
                          entry.algorithm as Algorithm,
                        )}`}
                      >
                        {formatAlgorithmName(entry.algorithm)}
                      </span>
                    ))}
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                        leaderCount > 1 ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-800"
                      }`}
                    >
                      {leaderCount > 1 ? `${leaderCount}-way practical tie` : "Clear leader"}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-sm font-medium text-slate-700 transition-transform group-open:rotate-90">
                      &rsaquo;
                    </span>
                  </div>
                </summary>

                <div className="border-t border-slate-200 px-4 pb-4 pt-3">
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs uppercase tracking-[0.16em] text-slate-500">
                          <th className="pb-2 pr-3">Rank</th>
                          <th className="pb-2 pr-3">Algorithm</th>
                          <th className="pb-2 pr-3">Mean</th>
                          <th className="pb-2 pr-3">Std</th>
                          <th className="pb-2">Group</th>
                        </tr>
                      </thead>
                      <tbody>
                        {row.ranking.map((entry) => {
                          const tiedGroupSize = row.ranking.filter(
                            (candidate) => candidate.practical_tie_group === entry.practical_tie_group,
                          ).length;
                          return (
                            <tr key={`${row.metric_name}-${entry.algorithm}-detail`} className="border-t border-slate-100">
                              <td className="py-2 pr-3 font-semibold text-slate-900">#{entry.rank}</td>
                              <td className="py-2 pr-3 text-slate-700">{formatAlgorithmName(entry.algorithm)}</td>
                              <td className="py-2 pr-3 text-slate-700">
                                {formatMetricValue(row.metric_name, entry.mean)}
                              </td>
                              <td className="py-2 pr-3 text-slate-700">
                                {formatMetricValue(row.metric_name, entry.std)}
                              </td>
                              <td className="py-2 text-slate-700">
                                {tiedGroupSize > 1 ? `Tie group ${entry.practical_tie_group}` : "Standalone"}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </details>
            );
          })}
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-slate-200 p-4">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
            Comparison vs FIFO
          </h4>
          {!analysis.baseline_analysis.available ? (
            <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800">
              FIFO not included
            </span>
          ) : null}
        </div>
        {analysis.baseline_analysis.available ? (
          <div className="mb-4 space-y-2 text-sm text-slate-700">
            {analysis.baseline_analysis.baseline_headline_findings.map((finding) => (
              <p key={finding} className="rounded-2xl bg-slate-50 px-4 py-3">
                {finding}
              </p>
            ))}
          </div>
        ) : null}
        {analysis.baseline_analysis.available ? (
          <div className="space-y-4">
            {groupBaselineRowsByMetric(comparisonRows).map(({ metricName, displayLabel, rows }, index) => (
              <details
                key={metricName}
                open={index === 0}
                className="group rounded-2xl border border-slate-200 bg-white"
              >
                <summary className="flex cursor-pointer list-none flex-wrap items-start justify-between gap-3 p-4">
                  <div>
                    <h5 className="text-base font-semibold text-slate-900">
                      {displayLabel ?? formatMetricName(metricName)}
                    </h5>
                    <p className="mt-1 text-sm text-slate-600">Comparison against the FIFO baseline for this metric.</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                      FIFO reference: {formatMetricValue(metricName, rows[0]?.baseline_mean ?? 0)}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-sm font-medium text-slate-700 transition-transform group-open:rotate-90">
                      &rsaquo;
                    </span>
                  </div>
                </summary>

                <div className="border-t border-slate-200 px-4 pb-4 pt-3">
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs uppercase tracking-[0.16em] text-slate-500">
                          <th className="pb-2 pr-3">Algorithm</th>
                          <th className="pb-2 pr-3">Mean</th>
                          <th className="pb-2 pr-3">Diff</th>
                          <th className="pb-2 pr-3">Improvement</th>
                          <th className="pb-2">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((row) => (
                          <tr key={`${row.metric_name}-${row.algorithm}`} className="border-t border-slate-100">
                            <td className="py-2 pr-3 text-slate-700">{formatAlgorithmName(row.algorithm)}</td>
                            <td className="py-2 pr-3 text-slate-700">
                              {formatMetricValue(row.metric_name, row.algorithm_mean)}
                            </td>
                            <td className="py-2 pr-3 text-slate-700">
                              {formatMetricValue(row.metric_name, row.absolute_difference)}
                            </td>
                            <td className="py-2 pr-3 text-slate-700">
                              {row.improvement_percent === null ? "n/a" : `${row.improvement_percent.toFixed(1)}%`}
                            </td>
                            <td className="py-2">
                              <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusStyle(row.status)}`}>
                                {formatStatus(row.status)}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </details>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-600">
            FIFO baseline analysis is unavailable because FIFO was not part of the selected algorithm set.
          </p>
        )}
      </div>
    </div>
  );
}

function CategoryRankingPanel({
  title,
  ranking,
}: {
  title: string;
  ranking: ExperimentAnalysis["clinical_ranking"];
}) {
  return (
    <div className="rounded-2xl border border-slate-200 p-4">
      <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</h4>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.16em] text-slate-500">
              <th className="pb-2 pr-3">Rank</th>
              <th className="pb-2 pr-3">Algorithm</th>
              <th className="pb-2 pr-3">Total Score</th>
              <th className="pb-2">First Place Metrics</th>
            </tr>
          </thead>
          <tbody>
            {ranking.ranking.map((row) => (
              <tr key={`${title}-${row.algorithm}`} className="border-t border-slate-100">
                <td className="py-2 pr-3 font-semibold text-slate-900">#{row.rank}</td>
                <td className="py-2 pr-3 text-slate-700">{formatAlgorithmName(row.algorithm)}</td>
                <td className="py-2 pr-3 text-slate-700">{row.total_score}</td>
                <td className="py-2 text-slate-700">{row.first_place_metrics}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MetricSummaryCell({
  summary,
  emphasize,
  metricKey,
}: {
  summary: MetricSummary;
  emphasize: boolean;
  metricKey: ExperimentMetricKey;
}) {
  const formatValue = (value: number) =>
    metricKey === "average_resource_utilization" ? `${(value * 100).toFixed(1)}%` : value.toFixed(2);

  return (
    <div>
      <div className={`text-sm font-semibold ${emphasize ? "text-emerald-800" : "text-slate-900"}`}>
        mean {formatValue(summary.mean)}
      </div>
      <div className="text-xs text-slate-500">std {formatValue(summary.std)}</div>
      <div className="mt-1 text-xs text-slate-500">
        min {formatValue(summary.min)} · max {formatValue(summary.max)}
      </div>
    </div>
  );
}

function formatMetricName(metricName: string) {
  return metricName
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function metricDisplayLabel(metric: ExperimentMetricKey) {
  return {
    treated_patients: "Treated Patients",
    untreated_patients: "Untreated Patients",
    average_waiting_time: "Average Waiting Time",
    max_waiting_time: "Maximum Waiting Time",
    critical_late_patients: "Critical Late Patients",
    total_clinical_impact: "Total Clinical Impact",
    average_resource_utilization: "Average Resource Utilization",
    total_planning_overhead_time: "Total Planning Overhead Time",
    average_time_to_service_start: "Average Time To Service Start",
    patients_deteriorated_while_waiting: "Patients Deteriorated While Waiting",
    critical_patients_waited: "Critical Patients Waited",
    critical_patients_started_immediately: "Critical Patients Started Immediately",
    services_started_from_arrival: "Services Started From Arrival",
    services_started_from_service_end: "Services Started From Service End",
    number_of_initial_assessments: "Number Of Initial Assessments",
    services_started_from_deterioration: "Services Started From Deterioration",
    services_started_from_doctor_round: "Services Started From Doctor Round",
    average_time_to_initial_assessment: "Average Time To Initial Assessment",
    total_doctor_round_time: "Total Doctor Round Time",
    number_of_doctor_rounds: "Number Of Doctor Rounds",
    average_doctor_round_duration: "Average Doctor Round Duration",
  }[metric];
}

function metricDirectionFromAnalysis(metric: ExperimentMetricKey, analysis: ExperimentAnalysis) {
  return analysis.metric_directions[metric] ?? "neutral";
}

function algorithmBadgeStyle(algorithm: Algorithm) {
  if (algorithm === "fifo") return "bg-slate-100 text-slate-800";
  if (algorithm === "greedy") return "bg-teal-100 text-teal-800";
  if (algorithm === "astar") return "bg-amber-100 text-amber-900";
  if (algorithm === "simulated_annealing") return "bg-sky-100 text-sky-900";
  return "bg-rose-100 text-rose-800";
}

function groupBaselineRowsByMetric(rows: ExperimentAnalysis["baseline_analysis"]["comparisons_vs_baseline"]) {
  const groups = new Map<
    string,
    {
      metricName: string;
      displayLabel?: string;
      rows: typeof rows;
    }
  >();

  for (const row of rows) {
    const existing = groups.get(row.metric_name);
    if (existing) {
      existing.rows.push(row);
      continue;
    }
    groups.set(row.metric_name, {
      metricName: row.metric_name,
      displayLabel: row.display_label,
      rows: [row],
    });
  }

  return Array.from(groups.values());
}

function formatDirection(direction: string) {
  if (direction === "lower_is_better") return "Lower is better";
  if (direction === "higher_is_better") return "Higher is better";
  return "Neutral";
}

function formatMetricValue(metricName: string, value: number) {
  if (metricName === "average_resource_utilization") {
    return `${(value * 100).toFixed(1)}%`;
  }
  return value.toFixed(2);
}

function formatStatus(status: string) {
  if (status === "not_comparable") return "Not comparable";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function statusStyle(status: string) {
  if (status === "improved") return "bg-emerald-100 text-emerald-800";
  if (status === "regressed") return "bg-rose-100 text-rose-800";
  if (status === "tied") return "bg-slate-100 text-slate-700";
  return "bg-amber-100 text-amber-800";
}

function findBestAlgorithms(
  result: ExperimentComparisonResponse,
  metric: ExperimentMetricKey,
  better: "lower" | "higher",
) {
  const entries = result.algorithms.map((algorithm) => ({
    algorithm,
    value: result.results[algorithm][metric].mean,
  }));
  const bestValue =
    better === "lower"
      ? Math.min(...entries.map((entry) => entry.value))
      : Math.max(...entries.map((entry) => entry.value));
  return entries.filter((entry) => entry.value === bestValue).map((entry) => entry.algorithm);
}
