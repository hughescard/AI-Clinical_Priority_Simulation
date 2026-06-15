import type {
  ExperimentAnalysisResponse,
  ExperimentComparisonRequest,
  ExperimentComparisonResponse,
  HealthResponse,
  SimulationRequest,
  SimulationResponse,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const fallbackMessage = `Request failed with status ${response.status}`;
    try {
      const errorBody = (await response.json()) as { detail?: string };
      throw new Error(errorBody.detail ?? fallbackMessage);
    } catch {
      throw new Error(fallbackMessage);
    }
  }

  return (await response.json()) as T;
}

async function download(path: string, payload: unknown): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const fallbackMessage = `Request failed with status ${response.status}`;
    try {
      const errorBody = (await response.json()) as { detail?: string };
      throw new Error(errorBody.detail ?? fallbackMessage);
    } catch {
      throw new Error(fallbackMessage);
    }
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filenameMatch = disposition.match(/filename="([^"]+)"/);
  const filename = filenameMatch?.[1] ?? "export.dat";
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export const apiClient = {
  getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },
  runSimulation(payload: SimulationRequest): Promise<SimulationResponse> {
    return request<SimulationResponse>("/simulation/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  compareExperiments(payload: ExperimentComparisonRequest): Promise<ExperimentComparisonResponse> {
    return request<ExperimentComparisonResponse>("/experiments/compare", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  analyzeExperiments(payload: ExperimentComparisonRequest): Promise<ExperimentAnalysisResponse> {
    return request<ExperimentAnalysisResponse>("/experiments/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  downloadSimulationJson(payload: SimulationRequest): Promise<void> {
    return download("/simulation/export/json", payload);
  },
  downloadSimulationCsv(payload: SimulationRequest): Promise<void> {
    return download("/simulation/export/csv", payload);
  },
  downloadExperimentJson(payload: ExperimentComparisonRequest): Promise<void> {
    return download("/experiments/export/json", payload);
  },
  downloadExperimentCsv(payload: ExperimentComparisonRequest): Promise<void> {
    return download("/experiments/export/csv", payload);
  },
  downloadExperimentSummaryCsv(payload: ExperimentComparisonRequest): Promise<void> {
    return download("/experiments/export/summary-csv", payload);
  },
};

export { API_BASE_URL };
