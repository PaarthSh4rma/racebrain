import type {
  DataQuality,
  Gap,
  HistoricalAnalysisResponse,
  HistoricalDriver,
  HistoricalRaceStateResponse,
  HistoricalSession,
  ModelLapEvidence,
  ModelVersion,
  PaceRobustnessResult,
  Provenance,
  RaceState,
  SelectionAudit,
  TyreSlopeRobustnessResult,
} from "../types/historical";

type RecordValue = Record<string, unknown>;
const qualityLevels = new Set(["good", "degraded", "insufficient", "unknown"]);
const slopeSigns = new Set(["negative", "zero", "positive"]);
const paceUnavailableReasons = new Set(["insufficient_recent_clean_laps"]);
const tyreUnavailableReasons = new Set(["no_observations", "missing_tyre_annotation", "unknown_compound", "mixed_compound",
  "inconsistent_tyre_age_progression", "insufficient_clean_laps", "insufficient_tyre_age_span"]);
const robustnessUnavailableReasons = new Set(["point_estimate_unavailable", "invalid_diagnostic_refit"]);

const isRecord = (value: unknown): value is RecordValue => typeof value === "object" && value !== null && !Array.isArray(value);
const isString = (value: unknown): value is string => typeof value === "string";
const isNullableString = (value: unknown) => value === null || isString(value);
const isFiniteNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const isInteger = (value: unknown): value is number => isFiniteNumber(value) && Number.isInteger(value);
const isPositiveInteger = (value: unknown): value is number => isInteger(value) && value > 0;
const isNonnegativeInteger = (value: unknown): value is number => isInteger(value) && value >= 0;
const isNullablePositiveInteger = (value: unknown) => value === null || isPositiveInteger(value);
const isNullableNonnegativeInteger = (value: unknown) => value === null || isNonnegativeInteger(value);
const isStringArray = (value: unknown): value is string[] => Array.isArray(value) && value.every(isString);
const isNullableFiniteNumber = (value: unknown) => value === null || isFiniteNumber(value);
const isStringNumberRecord = (value: unknown) => isRecord(value) && Object.values(value).every(isNonnegativeInteger);
const isStringBooleanRecord = (value: unknown) => isRecord(value) && Object.values(value).every((item) => typeof item === "boolean");

function isExternalId(value: unknown) {
  return isRecord(value) && isString(value.provider) && isString(value.resource_type) && isString(value.value);
}

function isProvenance(value: unknown): value is Provenance {
  return isRecord(value) && isString(value.source) && isNullableString(value.observed_at)
    && isStringArray(value.transformations) && isStringArray(value.assumptions)
    && Array.isArray(value.external_ids) && value.external_ids.every(isExternalId);
}

function isQuality(value: unknown): value is DataQuality {
  return isRecord(value) && qualityLevels.has(String(value.level))
    && isNullableFiniteNumber(value.completeness)
    && isStringArray(value.warnings) && isStringArray(value.missing_fields);
}

function isGap(value: unknown): value is Gap {
  if (!isRecord(value)) return false;
  const secondsGap = isFiniteNumber(value.seconds) && value.seconds >= 0 && value.laps === null;
  const lapGap = value.seconds === null && isPositiveInteger(value.laps);
  return secondsGap || lapGap;
}

function isTyre(value: unknown) {
  return value === null || isRecord(value) && isString(value.compound)
    && isNonnegativeInteger(value.age_laps) && isNullablePositiveInteger(value.stint_number);
}

function isCompetitor(value: unknown) {
  return isRecord(value) && isString(value.competitor_id) && isString(value.observed_at)
    && isNullableString(value.driver_name) && isNullablePositiveInteger(value.position)
    && isNullableNonnegativeInteger(value.current_lap)
    && (value.gap_ahead === null || isGap(value.gap_ahead))
    && (value.gap_to_leader === null || isGap(value.gap_to_leader)) && isTyre(value.tyre)
    && (value.in_pit === null || typeof value.in_pit === "boolean") && isNullableNonnegativeInteger(value.pit_stop_count)
    && isQuality(value.data_quality) && Array.isArray(value.provenance) && value.provenance.every(isProvenance)
    && Array.isArray(value.external_ids) && value.external_ids.every(isExternalId);
}

function isWeather(value: unknown) {
  return value === null || isRecord(value) && isString(value.observed_at)
    && [value.air_temperature_c, value.track_temperature_c, value.humidity_fraction, value.wind_speed_mps].every(isNullableFiniteNumber)
    && (value.rainfall_detected === null || typeof value.rainfall_detected === "boolean");
}

function isTrackStatus(value: unknown) {
  return value === null || isRecord(value) && isString(value.status) && isString(value.observed_at)
    && Array.isArray(value.provenance) && value.provenance.every(isProvenance);
}

function isRaceState(value: unknown): value is RaceState {
  if (!isRecord(value)) return false;
  const session = value.session;
  return isString(value.observation_cutoff)
    && isRecord(session) && isString(session.name) && isRecord(session.event) && isString(session.event.name)
    && Array.isArray(value.competitors) && value.competitors.every(isCompetitor)
    && isQuality(value.data_quality) && Array.isArray(value.provenance) && value.provenance.every(isProvenance)
    && isWeather(value.weather) && isTrackStatus(value.track_status);
}

function isModelVersion(value: unknown): value is ModelVersion {
  return isRecord(value) && isString(value.model_name) && isString(value.version) && isString(value.config_hash)
    && value.config_hash.startsWith("sha256:");
}

function isEvidenceWindow(value: unknown) {
  return isRecord(value) && isString(value.started_at) && isString(value.ended_at)
    && isPositiveInteger(value.first_lap) && isPositiveInteger(value.last_lap);
}

function isEstimateBase(value: unknown) {
  return isRecord(value) && isFiniteNumber(value.value) && isString(value.unit)
    && isModelVersion(value.model_version) && value.uncertainty === null && value.confidence === "unknown"
    && isStringArray(value.assumptions) && Array.isArray(value.provenance) && value.provenance.every(isProvenance)
    && isString(value.competitor_id) && isString(value.as_of) && isPositiveInteger(value.sample_count)
    && isEvidenceWindow(value.evidence_window) && isQuality(value.data_quality) && isStringArray(value.limitations);
}

function isFitDiagnostics(value: unknown, tyre = false) {
  if (!isRecord(value) || !isString(value.competitor_id) || !isString(value.as_of)
    || !isNonnegativeInteger(value.candidate_laps) || !isNonnegativeInteger(value.included_laps)
    || !isNonnegativeInteger(value.excluded_laps) || !isNullableFiniteNumber(value.residual_median_s)
    || !isNullableFiniteNumber(value.residual_median_absolute_s) || !isStringArray(value.warnings)
    || !isModelVersion(value.model_version) || !isQuality(value.data_quality)
    || !Array.isArray(value.provenance) || !value.provenance.every(isProvenance)) return false;
  return !tyre || isNullableString(value.compound) && isNullablePositiveInteger(value.stint_number)
    && isNullableNonnegativeInteger(value.minimum_tyre_age_laps)
    && isNullableNonnegativeInteger(value.maximum_tyre_age_laps)
    && isNullableNonnegativeInteger(value.tyre_age_span_laps) && isNullableFiniteNumber(value.intercept_s);
}

function isSelectionAudit(value: unknown): value is SelectionAudit {
  return isRecord(value) && Array.isArray(value.hard_exclusions)
    && value.hard_exclusions.every((item) => isRecord(item) && isString(item.reason) && isPositiveInteger(item.lap_count))
    && Array.isArray(value.warning_exclusions)
    && value.warning_exclusions.every((item) => isRecord(item) && isString(item.warning) && isPositiveInteger(item.lap_count));
}

function isPointFit(value: unknown, tyre = false) {
  if (!isRecord(value) || !isString(value.competitor_id) || !isFitDiagnostics(value.diagnostics, tyre)
    || !isSelectionAudit(value.selection_audit)
    || !(value.unavailable_reason === null || (tyre ? tyreUnavailableReasons : paceUnavailableReasons).has(String(value.unavailable_reason)))) return false;
  if (value.estimate === null) return value.unavailable_reason !== null;
  if (!isRecord(value.estimate) || !isEstimateBase(value.estimate) || value.unavailable_reason !== null) return false;
  if (value.estimate.unit !== (tyre ? "s/lap/lap" : "s/lap")) return false;
  return !tyre || isRecord(value.estimate) && isString(value.estimate.compound)
    && isPositiveInteger(value.estimate.stint_number)
    && isNonnegativeInteger(value.estimate.minimum_tyre_age_laps)
    && isNonnegativeInteger(value.estimate.maximum_tyre_age_laps);
}

function isRobustnessBase(value: unknown, tyre = false) {
  return isRecord(value) && isString(value.competitor_id) && isString(value.as_of)
    && isModelVersion(value.point_model_version) && isModelVersion(value.robustness_model_version)
    && isPointFit(value.point_fit, tyre)
    && (value.unavailable_reason === null || robustnessUnavailableReasons.has(String(value.unavailable_reason)))
    && isQuality(value.data_quality) && Array.isArray(value.provenance) && value.provenance.every(isProvenance)
    && isStringArray(value.limitations);
}

function isPaceResult(value: unknown): value is PaceRobustnessResult {
  if (!isRobustnessBase(value) || !isRecord(value)) return false;
  if (value.diagnostics === null) return value.unavailable_reason !== null;
  const diagnostic = value.diagnostics;
  return value.unavailable_reason === null && isRecord(diagnostic) && diagnostic.quantile_method === "linear_interpolation"
    && isRecord(diagnostic.quantiles) && [diagnostic.quantiles.p10, diagnostic.quantiles.p50, diagnostic.quantiles.p90].every(isFiniteNumber)
    && isPositiveInteger(diagnostic.quantiles.sample_count) && isFiniteNumber(diagnostic.minimum_lap_time_s)
    && isFiniteNumber(diagnostic.maximum_lap_time_s) && isFiniteNumber(diagnostic.p90_p10_spread_s);
}

function isTyreResult(value: unknown): value is TyreSlopeRobustnessResult {
  if (!isRobustnessBase(value, true) || !isRecord(value)) return false;
  if (value.diagnostics === null) return value.unavailable_reason !== null;
  const diagnostic = value.diagnostics;
  return value.unavailable_reason === null && isRecord(diagnostic)
    && isFiniteNumber(diagnostic.nominal_slope_s_per_lap_per_lap) && slopeSigns.has(String(diagnostic.nominal_sign))
    && isFiniteNumber(diagnostic.zero_tolerance_s_per_lap_per_lap)
    && Array.isArray(diagnostic.leave_one_out_refits)
    && diagnostic.leave_one_out_refits.every((item) => isRecord(item) && isPositiveInteger(item.omitted_lap_number)
      && isFiniteNumber(item.slope_s_per_lap_per_lap) && slopeSigns.has(String(item.sign)))
    && isPositiveInteger(diagnostic.leave_one_out_refit_count)
    && isFiniteNumber(diagnostic.leave_one_out_min_s_per_lap_per_lap)
    && isFiniteNumber(diagnostic.leave_one_out_max_s_per_lap_per_lap)
    && isRecord(diagnostic.sensitivity_envelope) && isFiniteNumber(diagnostic.sensitivity_envelope.lower)
    && isFiniteNumber(diagnostic.sensitivity_envelope.upper) && diagnostic.sensitivity_envelope.coverage === null
    && isString(diagnostic.sensitivity_envelope.method) && typeof diagnostic.sign_stable === "boolean"
    && isRecord(diagnostic.sign_counts) && [diagnostic.sign_counts.negative, diagnostic.sign_counts.zero, diagnostic.sign_counts.positive].every(isNonnegativeInteger)
    && isFiniteNumber(diagnostic.maximum_absolute_deviation_s_per_lap_per_lap)
    && isPositiveInteger(diagnostic.most_influential_omitted_lap);
}

function isPaceField(value: unknown): value is HistoricalAnalysisResponse["pace"] {
  return isRecord(value) && isString(value.as_of)
    && isModelVersion(value.point_model_version) && isModelVersion(value.robustness_model_version)
    && Array.isArray(value.competitors) && value.competitors.every(isPaceResult);
}

function isTyreField(value: unknown): value is HistoricalAnalysisResponse["tyre_age_slope"] {
  return isRecord(value) && isString(value.as_of)
    && isModelVersion(value.point_model_version) && isModelVersion(value.robustness_model_version)
    && Array.isArray(value.competitors) && value.competitors.every(isTyreResult);
}

function isReconstructionDiagnostics(value: unknown) {
  return isRecord(value) && isNonnegativeInteger(value.bounded_pit_lane_passages) && isStringBooleanRecord(value.cache_hits);
}

function isModellingDiagnostics(value: unknown) {
  if (!isRecord(value) || !isStringNumberRecord(value.admission_rejections) || !isStringBooleanRecord(value.feed_cache_hits)) return false;
  const numeric = ["source_lap_rows", "admitted_observations", "rows_bounded_out", "foreign_session_rows",
    "unmapped_competitor_rows", "exact_duplicate_laps", "conflicting_laps", "future_stint_starts",
    "ambiguous_stint_annotations", "tyre_annotations", "weather_alignments", "race_control_alignments",
    "gap_alignments", "pit_lane_affected_observations"];
  return numeric.every((key) => isNonnegativeInteger(value[key]));
}

function isModelLapEvidence(value: unknown): value is ModelLapEvidence {
  return isRecord(value) && Array.isArray(value.candidate_laps) && value.candidate_laps.every(isPositiveInteger)
    && Array.isArray(value.included_laps) && value.included_laps.every(isPositiveInteger)
    && Array.isArray(value.excluded_laps) && value.excluded_laps.every((item) => isRecord(item)
      && isPositiveInteger(item.lap_number) && isStringArray(item.reasons) && item.reasons.length > 0);
}

function isCompetitorEvidence(value: unknown): value is HistoricalAnalysisResponse["evidence"][number] {
  return isRecord(value) && isString(value.competitor_id)
    && isModelLapEvidence(value.pace) && isModelLapEvidence(value.tyre_age_slope);
}

export function parseSessions(value: unknown): HistoricalSession[] {
  if (!Array.isArray(value) || !value.every((item) => isRecord(item) && isPositiveInteger(item.session_key)
    && isPositiveInteger(item.meeting_key) && isInteger(item.year) && isString(item.event_name)
    && isString(item.country_name) && isString(item.location) && isString(item.session_name)
    && isNullableString(item.session_type))) throw new Error("The server returned malformed session data.");
  return value as HistoricalSession[];
}

export function parseDrivers(value: unknown): HistoricalDriver[] {
  if (!Array.isArray(value) || !value.every((item) => isRecord(item) && isPositiveInteger(item.driver_number)
    && isString(item.full_name) && isNullableString(item.name_acronym) && isNullableString(item.team_name))) {
    throw new Error("The server returned malformed driver data.");
  }
  return value as HistoricalDriver[];
}

export function parseDecisionLaps(value: unknown): number[] {
  if (!isRecord(value) || !Array.isArray(value.laps) || !value.laps.every(isPositiveInteger)) {
    throw new Error("The server returned malformed decision-lap data.");
  }
  return value.laps;
}

export function parseRaceState(value: unknown): HistoricalRaceStateResponse {
  if (!isRecord(value) || !isRaceState(value.race_state) || !isReconstructionDiagnostics(value.diagnostics)) {
    throw new Error("The server returned malformed historical race-state data.");
  }
  return value as unknown as HistoricalRaceStateResponse;
}

export function parseHistoricalAnalysis(value: unknown): HistoricalAnalysisResponse {
  if (!isRecord(value) || !isRaceState(value.race_state)
    || !isReconstructionDiagnostics(value.reconstruction_diagnostics)
    || !isModellingDiagnostics(value.modelling_diagnostics)
    || !isPaceField(value.pace) || !isTyreField(value.tyre_age_slope)
    || !Array.isArray(value.evidence) || !value.evidence.every(isCompetitorEvidence)) {
    throw new Error("The server returned malformed historical analysis data.");
  }
  const paceField = value.pace;
  const tyreField = value.tyre_age_slope;
  const evidence = value.evidence;
  const cutoff = value.race_state.observation_cutoff;
  const canonical = value.race_state.competitors.map((item) => item.competitor_id).sort();
  const paceIds = paceField.competitors.map((item) => item.competitor_id);
  const tyreIds = tyreField.competitors.map((item) => item.competitor_id);
  const evidenceIds = evidence.map((item) => item.competitor_id);
  const uniqueCanonical = new Set(canonical).size === canonical.length;
  const nestedPace = paceField.competitors.every((item) => resultReconciles(item, cutoff, paceField.point_model_version)
    && (item.diagnostics === null || item.point_fit.estimate !== null
      && item.diagnostics.quantiles.p50 === item.point_fit.estimate.value
      && item.diagnostics.quantiles.sample_count === item.point_fit.estimate.sample_count));
  const nestedTyre = tyreField.competitors.every((item) => resultReconciles(item, cutoff, tyreField.point_model_version)
    && (item.diagnostics === null || item.point_fit.estimate !== null
      && item.diagnostics.nominal_slope_s_per_lap_per_lap === item.point_fit.estimate.value
      && item.diagnostics.leave_one_out_refit_count === item.diagnostics.leave_one_out_refits.length));
  const paceById = new Map(paceField.competitors.map((item) => [item.competitor_id, item.point_fit.diagnostics]));
  const tyreById = new Map(tyreField.competitors.map((item) => [item.competitor_id, item.point_fit.diagnostics]));
  const evidenceReconciles = evidence.every((item) => {
    const pace = paceById.get(item.competitor_id);
    const tyre = tyreById.get(item.competitor_id);
    return pace !== undefined && tyre !== undefined && item.pace.candidate_laps.length === pace.candidate_laps
      && item.pace.included_laps.length === pace.included_laps
      && item.pace.excluded_laps.length === pace.excluded_laps
      && item.tyre_age_slope.candidate_laps.length === tyre.candidate_laps
      && item.tyre_age_slope.included_laps.length === tyre.included_laps
      && item.tyre_age_slope.excluded_laps.length === tyre.excluded_laps;
  });
  if (!uniqueCanonical || paceField.as_of !== cutoff || tyreField.as_of !== cutoff
    || JSON.stringify(paceIds) !== JSON.stringify(canonical) || JSON.stringify(tyreIds) !== JSON.stringify(canonical)
    || JSON.stringify(evidenceIds) !== JSON.stringify(canonical) || !nestedPace || !nestedTyre || !evidenceReconciles) {
    throw new Error("The server returned inconsistent historical analysis data.");
  }
  return value as unknown as HistoricalAnalysisResponse;
}

function sameVersion(left: ModelVersion, right: ModelVersion) {
  return left.model_name === right.model_name && left.version === right.version && left.config_hash === right.config_hash;
}

function resultReconciles(
  result: PaceRobustnessResult | TyreSlopeRobustnessResult,
  cutoff: string,
  pointVersion: ModelVersion,
) {
  const fit = result.point_fit;
  const estimate = fit.estimate;
  return result.as_of === cutoff && fit.competitor_id === result.competitor_id
    && fit.diagnostics.competitor_id === result.competitor_id && fit.diagnostics.as_of === cutoff
    && fit.diagnostics.candidate_laps === fit.diagnostics.included_laps + fit.diagnostics.excluded_laps
    && sameVersion(result.point_model_version, pointVersion)
    && sameVersion(fit.diagnostics.model_version, pointVersion)
    && (estimate === null || estimate.competitor_id === result.competitor_id && estimate.as_of === cutoff
      && estimate.sample_count === fit.diagnostics.included_laps && sameVersion(estimate.model_version, pointVersion));
}
