import { API_URL, apiError } from "./config";
import type { HistoricalDriver, HistoricalRaceStateResponse, HistoricalSession } from "../types/historical";

async function getJson<T>(path: string, fallback: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { signal });
  if (!response.ok) throw await apiError(response, fallback);
  try {
    return (await response.json()) as T;
  } catch {
    throw new Error("The server returned malformed historical race data.");
  }
}

export async function getHistoricalSessions(year: number, signal?: AbortSignal) {
  const result = await getJson<unknown>(`/v2/historical/sessions?year=${year}`, "Unable to load historical sessions.", signal);
  if (!Array.isArray(result)) throw new Error("The server returned malformed session data.");
  return result as HistoricalSession[];
}

export async function getHistoricalDrivers(sessionKey: number, signal?: AbortSignal) {
  const result = await getJson<unknown>(`/v2/historical/sessions/${sessionKey}/drivers`, "Unable to load session drivers.", signal);
  if (!Array.isArray(result)) throw new Error("The server returned malformed driver data.");
  return result as HistoricalDriver[];
}

export async function getDecisionLaps(sessionKey: number, driverNumber: number, signal?: AbortSignal) {
  const result = await getJson<{ laps?: unknown }>(`/v2/historical/sessions/${sessionKey}/drivers/${driverNumber}/decision-laps`, "Unable to load decision laps.", signal);
  if (!Array.isArray(result.laps) || !result.laps.every((lap) => typeof lap === "number")) {
    throw new Error("The server returned malformed decision-lap data.");
  }
  return result.laps;
}

export async function reconstructHistoricalState(sessionKey: number, driverNumber: number, decisionLap: number, signal?: AbortSignal) {
  const response = await fetch(`${API_URL}/v2/historical/race-state`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_key: sessionKey, driver_number: driverNumber, decision_lap: decisionLap }),
    signal,
  });
  if (!response.ok) throw await apiError(response, "Historical race state could not be reconstructed.");
  const result = (await response.json()) as HistoricalRaceStateResponse;
  if (!result?.race_state || !Array.isArray(result.race_state.competitors)) {
    throw new Error("The server returned malformed historical race-state data.");
  }
  return result;
}
