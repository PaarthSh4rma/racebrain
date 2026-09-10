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
