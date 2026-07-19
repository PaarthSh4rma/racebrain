import type {
  Driver,
  LiveStrategyResponse,
  RaceSession,
} from "../types/raceData";
import { API_URL, apiError } from "./config";

export async function getSessions({
  year,
  countryName,
  sessionName = "Race",
}: {
  year: number;
  countryName: string;
  sessionName?: string;
}): Promise<RaceSession[]> {
  const params = new URLSearchParams({
    year: String(year),
    country_name: countryName,
    session_name: sessionName,
  });

  const response = await fetch(`${API_URL}/race-data/sessions?${params}`);

  if (!response.ok) {
    throw await apiError(response, "Failed to search OpenF1 sessions.");
  }

  return response.json();
}

export async function getDrivers(sessionKey: number): Promise<Driver[]> {
  const response = await fetch(
    `${API_URL}/race-data/sessions/${sessionKey}/drivers`
  );

  if (!response.ok) {
    throw await apiError(response, "Failed to load drivers.");
  }

  return response.json();
}

export async function getLiveStrategy({
  sessionKey,
  driverNumber,
}: {
  sessionKey: number;
  driverNumber?: number | null;
}): Promise<LiveStrategyResponse> {
  const query =
    driverNumber !== null && driverNumber !== undefined
      ? `?driver_number=${driverNumber}`
      : "";

  const response = await fetch(
    `${API_URL}/live-strategy/session/${sessionKey}${query}`
  );

  if (!response.ok) {
    throw await apiError(response, "Failed to generate strategy.");
  }

  return response.json();
}
