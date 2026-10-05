export type Stint = {
  compound: string;
  laps: number;
};

export type Strategy = {
  strategy_id: number;
  strategy: Stint[];
  win_probability: number;
  win_percentage: number;
  preference_probability: number;
  preference_percentage: number;
  average_total_time: number;
  best_case: number;
  worst_case: number;
  std_dev: number;
};

export type SimulationInputs = {
  total_laps: number;
  base_lap_time: number;
  pit_loss: number;
  simulations: number;
  seed: number | null;
};

export type SimulationResult = {
  track: string;
  track_id: string;
  base_lap_time: number;
  pit_loss: number;
  degradation_multiplier: number;
  total_generated: number;
  deterministic_candidates_evaluated: number;
  simulations_per_strategy: number;
  // Legacy heuristic fields remain in the backend contract but are not
  // presented as confidence or win probability in the public product.
  confidence: string;
  win_gap_to_second: number;
  recommendation: string;
  best_strategy: Strategy;
  ranked_strategies: Strategy[];
  safety_car_probability: number;
  safety_car_simulations: number;
  safety_car_rate: number;
  seed: number | null;
};

export type TrackProfile = {
  id: string;
  name: string;
  base_lap_time: number;
  pit_loss: number;
  degradation_multiplier: number;
  safety_car_probability: number;
};
