import type {
  SimulationInputs,
  SimulationResult,
  TrackProfile,
} from "../types/racebrain";
import { API_URL, apiError } from "./config";

export async function getTrackProfiles(): Promise<TrackProfile[]> {
  const response = await fetch(`${API_URL}/tracks`);
  if (!response.ok) throw await apiError(response, "Failed to load track profiles.");
  const data = (await response.json()) as { tracks: TrackProfile[] };
  return data.tracks;
}

export async function getTrackProfile(trackId: string): Promise<TrackProfile> {
  const response = await fetch(`${API_URL}/tracks/${trackId}`);

  if (!response.ok) {
    throw await apiError(response, "Failed to load track profile.");
  }

  return response.json();
}

export async function runMonteCarloSimulation(
  track: string,
  inputs: SimulationInputs
): Promise<SimulationResult> {
  const response = await fetch(`${API_URL}/monte-carlo/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      track,
      total_laps: inputs.total_laps,
      simulations: inputs.simulations,
      base_lap_time: inputs.base_lap_time,
      pit_loss: inputs.pit_loss,
      lap_variance: 0.35,
      pit_variance: 1.5,
        include_one_stop: true,
        include_two_stop: true,
    }),
  });

  if (!response.ok) {
    throw await apiError(response, "Failed to run simulation.");
  }

  return response.json();
}
