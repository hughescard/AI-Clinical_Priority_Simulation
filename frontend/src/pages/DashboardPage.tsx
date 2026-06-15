import { useEffect, useState } from "react";

import { apiClient, API_BASE_URL } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { ExperimentForm } from "../components/ExperimentForm";
import { ExperimentResults } from "../components/ExperimentResults";
import { Layout } from "../components/Layout";
import { LoadingState } from "../components/LoadingState";
import { SectionTabs } from "../components/SectionTabs";
import { SimulationForm } from "../components/SimulationForm";
import { SimulationResults } from "../components/SimulationResults";
import type {
  ExperimentAnalysis,
  ExperimentComparisonRequest,
  ExperimentComparisonResponse,
  HealthResponse,
  SimulationRequest,
  SimulationResponse,
} from "../types";

export function DashboardPage() {
  const [activeTab, setActiveTab] = useState<"simulation" | "experiments">("simulation");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [simulation, setSimulation] = useState<SimulationResponse | null>(null);
  const [simulationRequest, setSimulationRequest] = useState<SimulationRequest | null>(null);
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationError, setSimulationError] = useState<string | null>(null);
  const [simulationExportError, setSimulationExportError] = useState<string | null>(null);
  const [experiment, setExperiment] = useState<ExperimentComparisonResponse | null>(null);
  const [experimentAnalysis, setExperimentAnalysis] = useState<ExperimentAnalysis | null>(null);
  const [experimentRequest, setExperimentRequest] = useState<ExperimentComparisonRequest | null>(null);
  const [experimentLoading, setExperimentLoading] = useState(false);
  const [experimentError, setExperimentError] = useState<string | null>(null);
  const [experimentExportError, setExperimentExportError] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .getHealth()
      .then((response) => {
        setHealth(response);
        setHealthError(null);
      })
      .catch((error: Error) => {
        setHealthError(error.message);
      });
  }, []);

  async function handleSimulationSubmit(payload: SimulationRequest) {
    if (payload.duration_minutes <= 0 || Number.isNaN(payload.duration_minutes)) {
      setSimulationError("Duration must be a positive number of minutes.");
      return;
    }
    if (Number.isNaN(payload.seed)) {
      setSimulationError("Seed must be a valid number.");
      return;
    }
    setSimulationLoading(true);
    setSimulationError(null);
    setSimulationExportError(null);
    try {
      const response = await apiClient.runSimulation(payload);
      setSimulation(response);
      setSimulationRequest(payload);
    } catch (error) {
      setSimulationError(error instanceof Error ? error.message : "Simulation request failed.");
    } finally {
      setSimulationLoading(false);
    }
  }

  async function handleExperimentSubmit(payload: ExperimentComparisonRequest) {
    if (payload.algorithms.length === 0) {
      setExperimentError("Select at least one algorithm for comparison.");
      return;
    }
    if (payload.replications <= 0 || Number.isNaN(payload.replications)) {
      setExperimentError("Replications must be a positive integer.");
      return;
    }
    if (payload.duration_minutes <= 0 || Number.isNaN(payload.duration_minutes)) {
      setExperimentError("Duration must be a positive number of minutes.");
      return;
    }
    setExperimentLoading(true);
    setExperimentError(null);
    setExperimentExportError(null);
    setExperimentAnalysis(null);
    try {
      const response = await apiClient.analyzeExperiments(payload);
      setExperiment(response.comparison);
      setExperimentAnalysis(response.analysis);
      setExperimentRequest(payload);
    } catch (error) {
      setExperimentError(error instanceof Error ? error.message : "Experiment request failed.");
      setExperiment(null);
    } finally {
      setExperimentLoading(false);
    }
  }

  async function handleSimulationExport(
    exporter: (payload: SimulationRequest) => Promise<void>,
    payload: SimulationRequest,
  ) {
    setSimulationExportError(null);
    try {
      await exporter(payload);
    } catch (error) {
      setSimulationExportError(error instanceof Error ? error.message : "Simulation export failed.");
    }
  }

  async function handleExperimentExport(
    exporter: (payload: ExperimentComparisonRequest) => Promise<void>,
    payload: ExperimentComparisonRequest,
  ) {
    setExperimentExportError(null);
    try {
      await exporter(payload);
    } catch (error) {
      setExperimentExportError(error instanceof Error ? error.message : "Experiment export failed.");
    }
  }

  const status = (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm shadow-sm">
      <p className="font-medium text-slate-700">Backend</p>
      <p className="mt-1 text-slate-500">{API_BASE_URL}</p>
      <p className={`mt-2 font-semibold ${health ? "text-emerald-700" : "text-rose-700"}`}>
        {health ? `Healthy: ${health.status}` : healthError ?? "Checking health..."}
      </p>
    </div>
  );

  return (
    <Layout status={status}>
      <SectionTabs activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "simulation" ? (
        <>
          <section className="panel p-6">
            <div className="mb-5">
              <h2 className="text-2xl font-semibold text-slate-950">Single Simulation</h2>
              <p className="mt-1 text-sm text-slate-600">
                Run one discrete-event scenario and inspect the clinical, operational, and planning outputs.
              </p>
            </div>
            <SimulationForm
              loading={simulationLoading}
              onSubmit={handleSimulationSubmit}
              error={simulationError}
            />
          </section>

          {simulationLoading ? (
            <LoadingState
              title="Running simulation"
              description="The backend is processing the emergency room event queue and updating doctor rounds, resources, and patient deterioration."
            />
          ) : simulation && simulationRequest ? (
            <div className="panel p-6">
              <div className="mb-5">
                <h2 className="text-2xl font-semibold text-slate-950">Simulation Results</h2>
              </div>
              <SimulationResults
                result={simulation}
                request={simulationRequest}
                onDownloadJson={(payload) => handleSimulationExport(apiClient.downloadSimulationJson, payload)}
                onDownloadCsv={(payload) => handleSimulationExport(apiClient.downloadSimulationCsv, payload)}
                exportError={simulationExportError}
              />
            </div>
          ) : (
            <EmptyState
              title="No simulation executed yet"
              description="Configure an algorithm, scenario, seed, and duration, then run a simulation to inspect the emergency department timeline and summary metrics."
            />
          )}
        </>
      ) : (
        <>
          <section className="panel p-6">
            <div className="mb-5">
              <h2 className="text-2xl font-semibold text-slate-950">Experiment Comparison</h2>
              <p className="mt-1 text-sm text-slate-600">
                Compare algorithms over multiple replications using the same scenario settings and seed schedule.
              </p>
            </div>
            <ExperimentForm
              loading={experimentLoading}
              onSubmit={handleExperimentSubmit}
              error={experimentError}
            />
          </section>

          {experimentLoading ? (
            <LoadingState
              title="Running comparison"
              description="Multiple seeded replications are being executed for each selected algorithm and aggregated into comparative metrics."
            />
          ) : experiment && experimentRequest ? (
            <div className="panel p-6">
              <div className="mb-5">
                <h2 className="text-2xl font-semibold text-slate-950">Experiment Results</h2>
              </div>
              <ExperimentResults
                result={experiment}
                analysis={experimentAnalysis}
                request={experimentRequest}
                onDownloadJson={(payload) => handleExperimentExport(apiClient.downloadExperimentJson, payload)}
                onDownloadCsv={(payload) => handleExperimentExport(apiClient.downloadExperimentCsv, payload)}
                onDownloadSummaryCsv={(payload) =>
                  handleExperimentExport(apiClient.downloadExperimentSummaryCsv, payload)
                }
                exportError={experimentExportError}
              />
            </div>
          ) : (
            <EmptyState
              title="No comparison executed yet"
              description="Choose one or more algorithms and run a replicated experiment to compare waiting time, clinical impact, and planning overhead."
            />
          )}
        </>
      )}
    </Layout>
  );
}
