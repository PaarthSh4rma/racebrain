import type { SimulationResult } from "./racebrain";

export type AiResponse = {
  summary?: string;
  response?: string;
  recommendation_type?: string;
  risk_level?: string;
  key_factors?: string[];
  tradeoffs?: string[];
  pit_wall_call?: string;
  follow_up_questions?: string[];
  tools_used?: string[];
  answer_type?: string;
  points?: string[];
  analysis_used?: string;
};

export type ScenarioResponse = {
  summary: string;
  adjustments: Record<string, unknown>;
  comparison: {
    original_strategy: number;
    new_strategy: number;
    original_win_rate: number;
    new_win_rate: number;
    strategy_changed: boolean;
  } | null;
  modified_result?: SimulationResult;
};