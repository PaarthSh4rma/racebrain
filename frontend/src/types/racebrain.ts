export type Stint = {
  compound: string;
  laps: number;
};

export type Strategy = {
  strategy_id: number;
  strategy: Stint[];
  win_percentage: number;
  average_total_time: number;
  std_dev: number;
};

export type SimulationInputs = {
  total_laps: number;
  base_lap_time: number;
  pit_loss: number;
  simulations: number;
};

export type SimulationResult = {
  track: string;
  base_lap_time: number;
  pit_loss: number;
  degradation_multiplier: number;
  total_generated: number;
  deterministic_candidates_evaluated: number;
  simulations_per_strategy: number;
  confidence: string;
  win_gap_to_second: number;
  recommendation: string;
  best_strategy: Strategy;
  ranked_strategies: Strategy[];
  safety_car_probability: number;
  safety_car_simulations: number;
  safety_car_rate: number;
};

export type TrackProfile = {
  name: string;
  base_lap_time: number;
  pit_loss: number;
  degradation_multiplier: number;
  safety_car_probability: number;
};