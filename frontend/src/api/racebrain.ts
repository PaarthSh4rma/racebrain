import type {
  SimulationInputs,
  SimulationResult,
  TrackProfile,
} from "../types/racebrain";

const API_URL = "http://127.0.0.1:8000";

export async function getTrackProfile(trackId: string): Promise<TrackProfile> {
  const response = await fetch(`${API_URL}/tracks/${trackId}`);

  if (!response.ok) {
    throw new Error("Failed to load track profile");
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
      lap_variance: 0.35,
      pit_variance: 1.5,
      include_one_stop: true,
      include_two_stop: false,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to run simulation");
  }

  return response.json();
}