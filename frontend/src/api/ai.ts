import type { SimulationResult } from "../types/racebrain";
import type { AiResponse, ScenarioResponse } from "../types/ai";
import { API_URL, apiError } from "./config";

export async function explainSimulation(
  message: string,
  result: SimulationResult
): Promise<AiResponse> {
  const response = await fetch(`${API_URL}/ai/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      simulation_result: result,
    }),
  });

  if (!response.ok) throw await apiError(response, "Failed to explain simulation.");

  return response.json();
}

export async function explainSimulationWithLlm(
  message: string,
  result: SimulationResult
): Promise<AiResponse> {
  const response = await fetch(`${API_URL}/ai/llm-explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: message,
      simulation_result: result,
    }),
  });

  if (!response.ok) throw await apiError(response, "Failed to generate LLM explanation.");

  return response.json();
}

export async function runScenarioSimulation({
  message,
  track,
  totalLaps,
  simulations,
  result,
}: {
  message: string;
  track: string;
  totalLaps: number;
  simulations: number;
  result: SimulationResult;
}): Promise<ScenarioResponse> {
  const response = await fetch(`${API_URL}/ai/scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: message,
      track,
      total_laps: totalLaps,
      simulations,
      original_result: result,
    }),
  });

  if (!response.ok) throw await apiError(response, "Failed to run scenario simulation.");

  return response.json();
}
