import type {
  Driver,
  LiveStrategyResponse,
  RaceSession,
} from "../types/raceData";

const API_URL = "http://127.0.0.1:8000";

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
    throw new Error("Failed to fetch sessions");
  }

  return response.json();
}

export async function getDrivers(sessionKey: number): Promise<Driver[]> {
  const response = await fetch(
    `${API_URL}/race-data/sessions/${sessionKey}/drivers`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch drivers");
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
    throw new Error("Failed to fetch live strategy");
  }

  return response.json();
}