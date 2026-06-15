export type Algorithm = "fifo" | "greedy" | "astar" | "cpsat" | "simulated_annealing";
export type Scenario = "normal" | "high_demand" | "limited_resources";
export type DataSource =
  | "synthetic"
  | "mimic_iv_ed_sample"
  | "mietic_sample"
  | "mimic_iv_ed"
  | "mietic";

export interface ResourceConfigEntry {
  id: string;
  capacity: number;
  enabled: boolean;
}

export interface AdvancedScenarioConfig {
  resources: ResourceConfigEntry[];
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface SimulationRequest {
  algorithm: Algorithm;
  scenario: Scenario;
  seed: number;
  data_source: DataSource;
  duration_minutes: number;
  advanced_config?: AdvancedScenarioConfig;
}

export interface ResourceSummary {
  capacity: number;
  final_in_use: number;
  final_available: number;
  peak_in_use: number;
  average_utilization: number;
  status: "available" | "constrained" | "fully_allocated" | string;
}

export interface TimelineResourceSnapshot {
  capacity: number;
  in_use: number;
  available: number;
}

export interface TimelineEvent {
  time: number;
  event_type: string;
  patient_id?: string | null;
  status?: string | null;
  algorithm?: Algorithm;
  trigger?: string;
  round_duration?: number;
  planning_overhead?: number;
  waiting_patient_count?: number;
  active_patient_count?: number;
  active_service_count?: number;
  note?: string;
  risk_level?: number;
  current_risk?: number;
  arrival_time?: number;
  textual_risk_score?: number;
  clinical_category?: string | null;
  required_resources?: string[];
  selected_for_immediate_service?: boolean;
  critical_waiting?: boolean;
  resources_allocated?: string[];
  resources_released?: string[];
  affected_waiting_patients?: number;
  priority_changes?: string[];
  available_resources?: Record<string, number>;
  feasible_patient_count?: number;
  started_patient_count?: number;
  blocking_resources?: string[];
  message?: string;
  resources?: Record<string, TimelineResourceSnapshot>;
}

export interface WaitingReasonEvent {
  time: number;
  trigger?: string | null;
  blocking_resources: string[];
  available_resources: Record<string, number>;
  message?: string | null;
}

export interface PatientTrace {
  patient_id: string;
  arrival_time: number;
  initial_assessment_time?: number | null;
  time_to_initial_assessment?: number | null;
  service_start_time?: number | null;
  service_end_time?: number | null;
  waiting_time?: number | null;
  service_time?: number | null;
  final_status: string;
  clinical_category?: string | null;
  risk_level?: number | null;
  current_risk?: number | null;
  textual_risk_score?: number | null;
  deterioration_rate?: number | null;
  max_wait_time?: number | null;
  estimated_service_time?: number | null;
  required_resources: string[];
  allocated_resources: string[];
  resources_released: string[];
  service_start_trigger?: string | null;
  algorithm: Algorithm;
  deterioration_events_count: number;
  deterioration_times: number[];
  deteriorated_while_waiting: boolean;
  critical_waiting: boolean;
  immediate_service: boolean;
  llm_provider_used?: string | null;
  llm_explanation?: string | null;
  waiting_reason_events: WaitingReasonEvent[];
  timeline_event_ids: number[];
}

export interface SimulationMetrics {
  total_patients: number;
  treated_patients: number;
  untreated_patients: number;
  number_of_initial_assessments: number;
  services_started_from_arrival: number;
  services_started_from_service_end: number;
  services_started_from_deterioration: number;
  services_started_from_doctor_round: number;
  average_time_to_initial_assessment: number;
  average_time_to_service_start: number;
  patients_deteriorated_while_waiting: number;
  critical_patients_waited: number;
  critical_patients_started_immediately: number;
  average_waiting_time: number;
  max_waiting_time: number;
  average_length_of_stay: number;
  throughput_per_hour: number;
  high_risk_treatment_rate: number;
  critical_late_patients: number;
  total_clinical_impact: number;
  average_resource_utilization: number;
  total_doctor_round_time: number;
  number_of_doctor_rounds: number;
  average_doctor_round_duration: number;
  total_planning_overhead_time: number;
}

export interface SimulationResponse {
  algorithm: Algorithm;
  scenario: Scenario;
  seed: number;
  duration_minutes: number;
  data_source: DataSource;
  dataset_records_used?: number | null;
  dataset_name?: string | null;
  metrics: SimulationMetrics;
  resource_summary: Record<string, ResourceSummary>;
  active_resource_catalog: Record<string, ResourceConfigEntry>;
  advanced_config?: AdvancedScenarioConfig | null;
  patient_status_summary: Record<string, number>;
  event_counts: Record<string, number>;
  llm_provider_requested?: string | null;
  llm_provider_used?: string | null;
  llm_fallback_order?: string[];
  llm_fallback_count?: number;
  llm_cache_hits?: number;
  llm_cache_misses?: number;
  llm_provider_attempts?: Record<string, { successes: number; failures: number }>;
  llm_provider_retries?: Record<string, number>;
  patient_traces: PatientTrace[];
  timeline: TimelineEvent[];
}

export interface ExperimentComparisonRequest {
  algorithms: Algorithm[];
  scenario: Scenario;
  seed_start: number;
  data_source: DataSource;
  replications: number;
  duration_minutes: number;
  advanced_config?: AdvancedScenarioConfig;
}

export interface MetricSummary {
  mean: number;
  std: number;
  min: number;
  max: number;
}

export interface ExperimentRun {
  algorithm: Algorithm;
  seed: number;
  metrics: SimulationMetrics;
}

export type ExperimentMetricKey =
  | "number_of_initial_assessments"
  | "services_started_from_arrival"
  | "services_started_from_service_end"
  | "services_started_from_deterioration"
  | "services_started_from_doctor_round"
  | "average_time_to_initial_assessment"
  | "average_time_to_service_start"
  | "patients_deteriorated_while_waiting"
  | "critical_patients_waited"
  | "critical_patients_started_immediately"
  | "treated_patients"
  | "untreated_patients"
  | "average_waiting_time"
  | "max_waiting_time"
  | "critical_late_patients"
  | "total_clinical_impact"
  | "average_resource_utilization"
  | "total_doctor_round_time"
  | "number_of_doctor_rounds"
  | "average_doctor_round_duration"
  | "total_planning_overhead_time";

export type ExperimentResultByAlgorithm = Record<ExperimentMetricKey, MetricSummary>;

export interface ExperimentComparisonResponse {
  scenario: Scenario;
  seed_start: number;
  replications: number;
  duration_minutes: number;
  data_source: DataSource;
  advanced_config?: AdvancedScenarioConfig | null;
  algorithms: Algorithm[];
  results: Record<Algorithm, ExperimentResultByAlgorithm>;
  runs: ExperimentRun[];
}

export type AnalysisDirection = "lower_is_better" | "higher_is_better" | "neutral";
export type AnalysisStatus = "improved" | "regressed" | "tied" | "not_comparable";

export interface BaselineComparisonRow {
  metric_name: string;
  display_label?: string;
  direction: AnalysisDirection;
  baseline_algorithm: string;
  algorithm: string;
  baseline_mean: number;
  algorithm_mean: number;
  absolute_difference: number;
  improvement_percent: number | null;
  status: AnalysisStatus;
}

export interface BestMetricRow {
  metric_name: string;
  display_label?: string;
  direction: AnalysisDirection;
  best_algorithm: string | null;
  best_mean: number | null;
  ranking: Array<{
    rank: number;
    algorithm: string;
    mean: number;
    std: number;
    min: number;
    max: number;
    practical_tie_group: number;
  }>;
}

export interface MetricRankBreakdownRow {
  metric_name: string;
  display_label: string;
  rank: number;
  points: number;
}

export interface CategoryRankingRow {
  rank: number;
  algorithm: string;
  total_score: number;
  first_place_metrics: number;
  tied_first_place_metrics?: number;
  metric_rank_breakdown: MetricRankBreakdownRow[];
}

export interface PerMetricRankingRow {
  rank: number;
  algorithm: string;
  mean: number;
  std: number;
  min: number;
  max: number;
  practical_tie_group: number;
}

export interface PerMetricRanking {
  metric_name: string;
  display_label: string;
  direction: AnalysisDirection;
  tolerance_used: number;
  ranking: PerMetricRankingRow[];
}

export interface CategoryRanking {
  category: string;
  included_metrics: string[];
  ranking: CategoryRankingRow[];
}

export interface BalancedCategoryBreakdownRow {
  category: string;
  normalized_score: number;
  raw_total_score: number;
  applied_weight: number;
  weighted_contribution: number;
}

export interface BalancedOverallRankingRow {
  rank: number;
  algorithm: string;
  balanced_score: number;
  clinical_score: number;
  operational_score: number;
  computational_score: number;
  category_breakdown: BalancedCategoryBreakdownRow[];
}

export interface BaselineAnalysis {
  baseline_algorithm: string;
  available: boolean;
  comparisons_vs_baseline: BaselineComparisonRow[];
  baseline_headline_findings: string[];
}

export interface ExperimentAnalysis {
  clinical_ranking: CategoryRanking;
  operational_ranking: CategoryRanking;
  computational_ranking: CategoryRanking;
  balanced_overall_ranking: BalancedOverallRankingRow[];
  overall_ranking: BalancedOverallRankingRow[];
  per_metric_rankings: PerMetricRanking[];
  baseline_algorithm: string;
  baseline_available: boolean;
  metric_directions: Record<string, AnalysisDirection>;
  headline_findings: string[];
  best_by_metric: BestMetricRow[];
  comparisons_vs_baseline: BaselineComparisonRow[];
  baseline_analysis: BaselineAnalysis;
  practical_tie_tolerance?: number;
}

export interface ExperimentAnalysisResponse {
  comparison: ExperimentComparisonResponse;
  analysis: ExperimentAnalysis;
}
