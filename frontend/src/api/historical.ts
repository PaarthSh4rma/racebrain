import { API_URL, apiError } from "./config";
import type { DataQuality, Gap, HistoricalDriver, HistoricalRaceStateResponse, HistoricalSession, Provenance } from "../types/historical";

type RecordValue = Record<string, unknown>;
const isRecord = (value: unknown): value is RecordValue => typeof value === "object" && value !== null && !Array.isArray(value);
const isString = (value: unknown): value is string => typeof value === "string";
const isNullableString = (value: unknown) => value === null || isString(value);
const isFiniteNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const isPositiveInteger = (value: unknown): value is number => isFiniteNumber(value) && Number.isInteger(value) && value > 0;
const isNullablePositiveInteger = (value: unknown) => value === null || isPositiveInteger(value);
const isNullableNonnegativeInteger = (value: unknown) => value === null || isFiniteNumber(value) && Number.isInteger(value) && value >= 0;
const isStringArray = (value: unknown): value is string[] => Array.isArray(value) && value.every(isString);

function isExternalId(value: unknown) {
  return isRecord(value) && isString(value.provider) && isString(value.resource_type) && isString(value.value);
}

function isProvenance(value: unknown): value is Provenance {
  return isRecord(value) && isString(value.source) && isNullableString(value.observed_at)
    && isStringArray(value.transformations) && isStringArray(value.assumptions)
    && Array.isArray(value.external_ids) && value.external_ids.every(isExternalId);
}

function isQuality(value: unknown): value is DataQuality {
  return isRecord(value) && ["good", "degraded", "insufficient", "unknown"].includes(String(value.level))
    && (value.completeness === null || isFiniteNumber(value.completeness))
    && isStringArray(value.warnings) && isStringArray(value.missing_fields);
}

function isGap(value: unknown): value is Gap {
  if (!isRecord(value)) return false;
  const seconds = value.seconds;
  const laps = value.laps;
  const secondsGap = isFiniteNumber(seconds) && seconds >= 0 && laps === null;
  const lapGap = seconds === null && isPositiveInteger(laps);
  return secondsGap || lapGap;
}

const isNullableGap = (value: unknown) => value === null || isGap(value);

function isTyre(value: unknown) {
  return value === null || isRecord(value) && isString(value.compound)
    && isFiniteNumber(value.age_laps) && Number.isInteger(value.age_laps) && value.age_laps >= 0
    && isNullablePositiveInteger(value.stint_number);
}

function isCompetitor(value: unknown) {
  return isRecord(value) && isString(value.competitor_id) && isString(value.observed_at)
    && isNullableString(value.driver_name) && isNullablePositiveInteger(value.position)
    && (value.current_lap === null || isFiniteNumber(value.current_lap) && Number.isInteger(value.current_lap) && value.current_lap >= 0)
    && isNullableGap(value.gap_ahead) && isNullableGap(value.gap_to_leader) && isTyre(value.tyre)
    && (value.in_pit === null || typeof value.in_pit === "boolean") && isNullableNonnegativeInteger(value.pit_stop_count)
    && isQuality(value.data_quality) && Array.isArray(value.provenance) && value.provenance.every(isProvenance)
    && Array.isArray(value.external_ids) && value.external_ids.every(isExternalId);
}

function isWeather(value: unknown) {
  return value === null || isRecord(value) && isString(value.observed_at)
    && [value.air_temperature_c, value.track_temperature_c, value.humidity_fraction, value.wind_speed_mps].every((item) => item === null || isFiniteNumber(item))
    && (value.rainfall_detected === null || typeof value.rainfall_detected === "boolean");
}

function isTrackStatus(value: unknown) {
  return value === null || isRecord(value) && isString(value.status) && isString(value.observed_at)
    && Array.isArray(value.provenance) && value.provenance.every(isProvenance);
}

function parseSessions(value: unknown): HistoricalSession[] {
  if (!Array.isArray(value) || !value.every((item) => isRecord(item) && isPositiveInteger(item.session_key)
    && isFiniteNumber(item.year) && Number.isInteger(item.year) && isString(item.event_name)
    && isString(item.location) && isString(item.session_name))) {
    throw new Error("The server returned malformed session data.");
  }
  return value as HistoricalSession[];
}

function parseDrivers(value: unknown): HistoricalDriver[] {
  if (!Array.isArray(value) || !value.every((item) => isRecord(item) && isPositiveInteger(item.driver_number) && isString(item.full_name))) {
    throw new Error("The server returned malformed driver data.");
  }
  return value as HistoricalDriver[];
}

function parseDecisionLaps(value: unknown): number[] {
  if (!isRecord(value) || !Array.isArray(value.laps) || !value.laps.every(isPositiveInteger)) {
    throw new Error("The server returned malformed decision-lap data.");
  }
  return value.laps;
}

function parseRaceState(value: unknown): HistoricalRaceStateResponse {
  if (!isRecord(value) || !isRecord(value.race_state)) throw new Error("The server returned malformed historical race-state data.");
  const state = value.race_state;
  const session = state.session;
  const validSession = isRecord(session) && isString(session.name) && isRecord(session.event) && isString(session.event.name);
  if (!isString(state.observation_cutoff) || !validSession || !Array.isArray(state.competitors)
    || !state.competitors.every(isCompetitor) || !isQuality(state.data_quality)
    || !Array.isArray(state.provenance) || !state.provenance.every(isProvenance)
    || !isWeather(state.weather) || !isTrackStatus(state.track_status)
    || !isRecord(value.diagnostics) || !isFiniteNumber(value.diagnostics.bounded_pit_lane_passages)
    || !isRecord(value.diagnostics.cache_hits)) {
    throw new Error("The server returned malformed historical race-state data.");
  }
  return value as unknown as HistoricalRaceStateResponse;
}

async function getJson(path: string, fallback: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(`${API_URL}${path}`, { signal });
  if (!response.ok) throw await apiError(response, fallback);
  try { return await response.json(); }
  catch { throw new Error("The server returned malformed historical race data."); }
}

export async function getHistoricalSessions(year: number, signal?: AbortSignal) {
  return parseSessions(await getJson(`/v2/historical/sessions?year=${year}`, "Unable to load historical sessions.", signal));
}

export async function getHistoricalDrivers(sessionKey: number, signal?: AbortSignal) {
  return parseDrivers(await getJson(`/v2/historical/sessions/${sessionKey}/drivers`, "Unable to load session drivers.", signal));
}

export async function getDecisionLaps(sessionKey: number, driverNumber: number, signal?: AbortSignal) {
  return parseDecisionLaps(await getJson(`/v2/historical/sessions/${sessionKey}/drivers/${driverNumber}/decision-laps`, "Unable to load decision laps.", signal));
}

export async function reconstructHistoricalState(sessionKey: number, driverNumber: number, decisionLap: number, signal?: AbortSignal) {
  const response = await fetch(`${API_URL}/v2/historical/race-state`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_key: sessionKey, driver_number: driverNumber, decision_lap: decisionLap }), signal,
  });
  if (!response.ok) throw await apiError(response, "Historical race state could not be reconstructed.");
  try { return parseRaceState(await response.json()); }
  catch (error) {
    if (error instanceof Error && error.message.startsWith("The server returned malformed")) throw error;
    throw new Error("The server returned malformed historical race-state data.", { cause: error });
  }
}
