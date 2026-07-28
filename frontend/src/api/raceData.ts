import type {
  DriverSummary,
  HistoricalSession,
  ReplayAssessment,
} from "../types/raceData";
import { API_URL, apiError } from "./config";

export async function getHistoricalSessions({
  year,
  countryName,
}: {
  year: number;
  countryName: string;
}): Promise<HistoricalSession[]> {
  const params = new URLSearchParams({
    year: String(year),
    country_name: countryName,
  });
  const response = await fetch(`${API_URL}/replay/sessions?${params}`);
  if (!response.ok) {
    throw await apiError(response, "Failed to search historical sessions.");
  }
  return response.json();
}

export async function getSessionDrivers(
  sessionKey: number,
): Promise<DriverSummary[]> {
  const response = await fetch(`${API_URL}/replay/sessions/${sessionKey}/drivers`);
  if (!response.ok) {
    throw await apiError(response, "Failed to load session drivers.");
  }
  return response.json();
}

export async function getDecisionLaps(
  sessionKey: number,
  driverNumber: number,
): Promise<number[]> {
  const response = await fetch(
    `${API_URL}/replay/sessions/${sessionKey}/drivers/${driverNumber}/decision-laps`,
  );
  if (!response.ok) {
    throw await apiError(response, "Failed to load completed decision laps.");
  }
  const body = (await response.json()) as { laps: number[] };
  return body.laps;
}

export async function getReplayAssessment({
  sessionKey,
  driverNumber,
  decisionLap,
}: {
  sessionKey: number;
  driverNumber: number;
  decisionLap: number;
}): Promise<ReplayAssessment> {
  const response = await fetch(`${API_URL}/replay/assessment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_key: sessionKey,
      driver_number: driverNumber,
      decision_lap: decisionLap,
      seed: 2026,
    }),
  });
  if (!response.ok) {
    throw await apiError(response, "Failed to reconstruct this race moment.");
  }
  return response.json();
}
