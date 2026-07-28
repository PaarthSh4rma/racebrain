export type HistoricalSession = {
  session_key: number;
  session_name: string;
  session_type?: string | null;
  country_name?: string | null;
  circuit_short_name?: string | null;
  location?: string | null;
  year?: number | null;
  date_start?: string | null;
  date_end?: string | null;
};

export type DriverSummary = {
  driver_number: number;
  broadcast_name?: string | null;
  full_name?: string | null;
  name_acronym?: string | null;
  team_name?: string | null;
  team_colour?: string | null;
};

export type RecordCount = {
  included: number;
  ignored_future: number;
};

export type ReplaySnapshot = {
  session: HistoricalSession;
  driver: DriverSummary;
  decision_lap: number;
  available_decision_laps: number[];
  cutoff_timestamp: string | null;
  current_stint: {
    stint_number?: number | null;
    lap_start: number;
    lap_end?: number | null;
    compound?: string | null;
    tyre_age_at_start?: number | null;
  } | null;
  current_compound: string | null;
  estimated_tyre_age: number | null;
  pace: {
    recent_lap_times: number[];
    recent_average: number | null;
    previous_average: number | null;
    trend_seconds_per_lap: number | null;
    trend: "improving" | "stable" | "degrading" | "unknown";
  };
  weather: {
    air_temperature: number | null;
    track_temperature: number | null;
    humidity: number | null;
    wind_speed: number | null;
    rainfall_detected: boolean;
    trend: "dry" | "rain_detected" | "unknown";
  };
  race_control: {
    safety_car_active: boolean;
    red_flag_active: boolean;
    safety_car_events: number;
    red_flag_events: number;
    recent_messages: string[];
  };
  bounded_laps: Array<{
    lap_number: number;
    lap_duration: number | null;
    date_start: string | null;
  }>;
  bounded_stints: Array<{
    stint_number?: number | null;
    lap_start: number;
    lap_end?: number | null;
    compound?: string | null;
  }>;
  data_quality: {
    cutoff_source: string;
    latest_included_timestamp: string | null;
    records: Record<string, RecordCount>;
    warnings: string[];
    cache_hits: Record<string, boolean>;
  };
};

export type ReplayAssessment = {
  snapshot: ReplaySnapshot;
  recommendation: {
    recommendation: string;
    confidence: "low" | "medium" | "high";
    summary: string;
    tyre_risk: "low" | "medium" | "high" | "unknown";
    reasoning_factors: string[];
    evidence: Record<string, string | number | boolean | null>;
    limitations: string[];
  };
  alternatives: Array<{
    alternative: "pit_now" | "extend" | "hold";
    strategy_score: number;
    delta_to_recommended: number;
    uncertainty: number;
    tyre_risk: "low" | "medium" | "high" | "unknown";
    explanation: string;
  }>;
  recommended_alternative: "pit_now" | "extend" | "hold";
  seed: number | null;
  simulations: number;
};
