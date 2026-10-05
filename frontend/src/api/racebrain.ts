import type {
  SimulationInputs,
  SimulationResult,
  TrackProfile,
} from "../types/racebrain";
import { API_URL, apiError } from "./config";
import { parseSimulationResult, parseTrackProfile, parseTrackProfiles } from "./simulationValidation";

export const SCENARIO_SIMULATION_CONFIG = Object.freeze({
  lapVariance: 0.35,
  pitVariance: 1.5,
  includeOneStop: true,
  includeTwoStop: true,
  maximumEvaluatedCandidates: 10,
});

async function json(response: Response, message: string): Promise<unknown> {
  try { return await response.json(); }
  catch { throw new Error(message); }
}

export async function getTrackProfiles(signal?: AbortSignal): Promise<TrackProfile[]> {
  const response = await fetch(`${API_URL}/tracks`, { signal });
  if (!response.ok) throw await apiError(response, "Failed to load track profiles.");
  return parseTrackProfiles(await json(response, "The server returned malformed track-profile data."));
}

export async function getTrackProfile(trackId: string, signal?: AbortSignal): Promise<TrackProfile> {
  const response = await fetch(`${API_URL}/tracks/${trackId}`, { signal });

  if (!response.ok) {
    throw await apiError(response, "Failed to load track profile.");
  }

  return parseTrackProfile(await json(response, "The server returned malformed track-profile data."));
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
      lap_variance: SCENARIO_SIMULATION_CONFIG.lapVariance,
      pit_variance: SCENARIO_SIMULATION_CONFIG.pitVariance,
      seed: inputs.seed,
      include_one_stop: SCENARIO_SIMULATION_CONFIG.includeOneStop,
      include_two_stop: SCENARIO_SIMULATION_CONFIG.includeTwoStop,
    }),
  });

  if (!response.ok) {
    throw await apiError(response, "Failed to run simulation.");
  }

  return parseSimulationResult(await json(response, "The server returned malformed simulation data."));
}
