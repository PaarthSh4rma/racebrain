import { API_URL, apiError } from "./config";
import {
  parseDecisionLaps,
  parseDrivers,
  parseHistoricalAnalysis,
  parseRaceState,
  parseSessions,
} from "./historicalValidation";

async function getJson(path: string, fallback: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(`${API_URL}${path}`, { signal });
  if (!response.ok) throw await apiError(response, fallback);
  try { return await response.json(); }
  catch { throw new Error("The server returned malformed historical race data."); }
}

async function postDecisionPoint(path: string, sessionKey: number, driverNumber: number, decisionLap: number, fallback: string, signal?: AbortSignal) {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_key: sessionKey, driver_number: driverNumber, decision_lap: decisionLap }),
    signal,
  });
  if (!response.ok) throw await apiError(response, fallback);
  try { return await response.json(); }
  catch { throw new Error("The server returned malformed historical analysis data."); }
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
  return parseRaceState(await postDecisionPoint("/v2/historical/race-state", sessionKey, driverNumber, decisionLap, "Historical race state could not be reconstructed.", signal));
}

export async function analyzeHistoricalDecisionPoint(sessionKey: number, driverNumber: number, decisionLap: number, signal?: AbortSignal) {
  return parseHistoricalAnalysis(await postDecisionPoint("/v2/historical/analysis", sessionKey, driverNumber, decisionLap, "Historical provider temporarily unavailable.", signal));
}
