export type Gap = { seconds: number | null; laps: number | null };
export type ExternalId = { provider: string; resource_type: string; value: string };
export type Provenance = {
  source: string;
  observed_at: string | null;
  transformations: string[];
  assumptions: string[];
  external_ids: ExternalId[];
};
export type DataQuality = {
  level: "good" | "degraded" | "insufficient" | "unknown";
  completeness: number | null;
  warnings: string[];
  missing_fields: string[];
};
export type HistoricalSession = {
  session_key: number;
  meeting_key: number;
  year: number;
  event_name: string;
  country_name: string;
  location: string;
  session_name: string;
  session_type: string | null;
};
export type HistoricalDriver = {
  driver_number: number;
  full_name: string;
  name_acronym: string | null;
  team_name: string | null;
};
export type CarState = {
  competitor_id: string;
  observed_at: string;
  driver_name: string | null;
  position: number | null;
  current_lap: number | null;
  gap_ahead: Gap | null;
  gap_to_leader: Gap | null;
  tyre: { compound: string; age_laps: number; stint_number: number | null } | null;
  in_pit: boolean | null;
  pit_stop_count: number | null;
  data_quality: DataQuality;
  provenance: Provenance[];
  external_ids: ExternalId[];
};
export type RaceState = {
  session: { name: string; event: { name: string } };
  observation_cutoff: string;
  track_status: { status: string; observed_at: string; provenance: Provenance[] } | null;
  weather: {
    observed_at: string;
    air_temperature_c: number | null;
    track_temperature_c: number | null;
    humidity_fraction: number | null;
    wind_speed_mps: number | null;
    rainfall_detected: boolean | null;
  } | null;
  competitors: CarState[];
  data_quality: DataQuality;
  provenance: Provenance[];
};
export type HistoricalRaceStateResponse = {
  race_state: RaceState;
  diagnostics: { bounded_pit_lane_passages: number; cache_hits: Record<string, boolean> };
};

export type ModelVersion = {
  model_name: string;
  version: string;
  config_hash: string;
};

export type EvidenceWindow = {
  started_at: string;
  ended_at: string;
  first_lap: number;
  last_lap: number;
};

export type FitDiagnostics = {
  competitor_id: string;
  as_of: string;
  candidate_laps: number;
  included_laps: number;
  excluded_laps: number;
  residual_median_s: number | null;
  residual_median_absolute_s: number | null;
  warnings: string[];
  model_version: ModelVersion;
  data_quality: DataQuality;
  provenance: Provenance[];
};

export type SelectionAudit = {
  hard_exclusions: { reason: string; lap_count: number }[];
  warning_exclusions: { warning: string; lap_count: number }[];
};

type EstimateBase = {
  value: number;
  unit: string;
  model_version: ModelVersion;
  uncertainty: null;
  confidence: "unknown";
  assumptions: string[];
  provenance: Provenance[];
  competitor_id: string;
  as_of: string;
  sample_count: number;
  evidence_window: EvidenceWindow;
  data_quality: DataQuality;
  limitations: string[];
};

export type PaceEstimate = EstimateBase;

export type PaceUnavailableReason = "insufficient_recent_clean_laps";
export type TyreSlopeUnavailableReason =
  | "no_observations"
  | "missing_tyre_annotation"
  | "unknown_compound"
  | "mixed_compound"
  | "inconsistent_tyre_age_progression"
  | "insufficient_clean_laps"
  | "insufficient_tyre_age_span";
export type RobustnessUnavailableReason = "point_estimate_unavailable" | "invalid_diagnostic_refit";

export type TyreSlopeEstimate = EstimateBase & {
  compound: string;
  stint_number: number;
  minimum_tyre_age_laps: number;
  maximum_tyre_age_laps: number;
};

export type PacePointFit = {
  competitor_id: string;
  estimate: PaceEstimate | null;
  diagnostics: FitDiagnostics;
  selection_audit: SelectionAudit;
  unavailable_reason: PaceUnavailableReason | null;
};

export type TyreSlopeDiagnostics = FitDiagnostics & {
  compound: string | null;
  stint_number: number | null;
  minimum_tyre_age_laps: number | null;
  maximum_tyre_age_laps: number | null;
  tyre_age_span_laps: number | null;
  intercept_s: number | null;
};

export type TyreSlopePointFit = {
  competitor_id: string;
  estimate: TyreSlopeEstimate | null;
  diagnostics: TyreSlopeDiagnostics;
  selection_audit: SelectionAudit;
  unavailable_reason: TyreSlopeUnavailableReason | null;
};

export type PaceRobustnessResult = {
  competitor_id: string;
  as_of: string;
  point_model_version: ModelVersion;
  robustness_model_version: ModelVersion;
  point_fit: PacePointFit;
  diagnostics: {
    quantile_method: "linear_interpolation";
    quantiles: { p10: number; p50: number; p90: number; sample_count: number };
    minimum_lap_time_s: number;
    maximum_lap_time_s: number;
    p90_p10_spread_s: number;
  } | null;
  unavailable_reason: RobustnessUnavailableReason | null;
  data_quality: DataQuality;
  provenance: Provenance[];
  limitations: string[];
};

export type SlopeSign = "negative" | "zero" | "positive";

export type TyreSlopeRobustnessResult = {
  competitor_id: string;
  as_of: string;
  point_model_version: ModelVersion;
  robustness_model_version: ModelVersion;
  point_fit: TyreSlopePointFit;
  diagnostics: {
    nominal_slope_s_per_lap_per_lap: number;
    nominal_sign: SlopeSign;
    zero_tolerance_s_per_lap_per_lap: number;
    leave_one_out_refits: {
      omitted_lap_number: number;
      slope_s_per_lap_per_lap: number;
      sign: SlopeSign;
    }[];
    leave_one_out_refit_count: number;
    leave_one_out_min_s_per_lap_per_lap: number;
    leave_one_out_max_s_per_lap_per_lap: number;
    sensitivity_envelope: { lower: number; upper: number; coverage: null; method: string };
    sign_stable: boolean;
    sign_counts: { negative: number; zero: number; positive: number };
    maximum_absolute_deviation_s_per_lap_per_lap: number;
    most_influential_omitted_lap: number;
  } | null;
  unavailable_reason: RobustnessUnavailableReason | null;
  data_quality: DataQuality;
  provenance: Provenance[];
  limitations: string[];
};

export type HistoricalAnalysisResponse = {
  race_state: RaceState;
  reconstruction_diagnostics: {
    bounded_pit_lane_passages: number;
    cache_hits: Record<string, boolean>;
  };
  modelling_diagnostics: {
    source_lap_rows: number;
    admitted_observations: number;
    admission_rejections: Record<string, number>;
    rows_bounded_out: number;
    foreign_session_rows: number;
    unmapped_competitor_rows: number;
    exact_duplicate_laps: number;
    conflicting_laps: number;
    future_stint_starts: number;
    ambiguous_stint_annotations: number;
    tyre_annotations: number;
    weather_alignments: number;
    race_control_alignments: number;
    gap_alignments: number;
    pit_lane_affected_observations: number;
    feed_cache_hits: Record<string, boolean>;
  };
  pace: {
    as_of: string;
    point_model_version: ModelVersion;
    robustness_model_version: ModelVersion;
    competitors: PaceRobustnessResult[];
  };
  tyre_age_slope: {
    as_of: string;
    point_model_version: ModelVersion;
    robustness_model_version: ModelVersion;
    competitors: TyreSlopeRobustnessResult[];
  };
  evidence: {
    competitor_id: string;
    pace: ModelLapEvidence;
    tyre_age_slope: ModelLapEvidence;
  }[];
};

export type ModelLapEvidence = {
  candidate_laps: number[];
  included_laps: number[];
  excluded_laps: { lap_number: number; reasons: string[] }[];
};
