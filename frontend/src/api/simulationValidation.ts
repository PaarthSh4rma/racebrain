import type { SimulationResult, Strategy, TrackProfile } from "../types/racebrain";

type RecordValue = Record<string, unknown>;
const isRecord = (value: unknown): value is RecordValue => typeof value === "object" && value !== null && !Array.isArray(value);
const isString = (value: unknown): value is string => typeof value === "string";
const isFiniteNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const isPositive = (value: unknown): value is number => isFiniteNumber(value) && value > 0;
const isNonnegative = (value: unknown): value is number => isFiniteNumber(value) && value >= 0;
const isPositiveInteger = (value: unknown): value is number => isPositive(value) && Number.isInteger(value);
const isNonnegativeInteger = (value: unknown): value is number => isNonnegative(value) && Number.isInteger(value);
const isProbability = (value: unknown): value is number => isFiniteNumber(value) && value >= 0 && value <= 1;
const isPercentage = (value: unknown): value is number => isFiniteNumber(value) && value >= 0 && value <= 100;

function isTrackProfile(value: unknown): value is TrackProfile {
  return isRecord(value) && isString(value.id) && value.id.length > 0 && isString(value.name) && value.name.length > 0
    && isPositive(value.base_lap_time) && isNonnegative(value.pit_loss) && isPositive(value.degradation_multiplier)
    && isProbability(value.safety_car_probability);
}

function isStrategy(value: unknown): value is Strategy {
  return isRecord(value) && isPositiveInteger(value.strategy_id)
    && Array.isArray(value.strategy) && value.strategy.length > 0
    && value.strategy.every((stint) => isRecord(stint) && ["soft", "medium", "hard"].includes(String(stint.compound)) && isPositiveInteger(stint.laps))
    && isProbability(value.win_probability) && isPercentage(value.win_percentage)
    && isProbability(value.preference_probability) && isPercentage(value.preference_percentage)
    && isPositive(value.average_total_time) && isPositive(value.best_case) && isPositive(value.worst_case)
    && isNonnegative(value.std_dev) && value.best_case <= value.average_total_time && value.average_total_time <= value.worst_case;
}

export function parseTrackProfiles(value: unknown): TrackProfile[] {
  if (!isRecord(value) || !Array.isArray(value.tracks) || !value.tracks.every(isTrackProfile)) {
    throw new Error("The server returned malformed track-profile data.");
  }
  return value.tracks;
}

export function parseTrackProfile(value: unknown): TrackProfile {
  if (!isTrackProfile(value)) throw new Error("The server returned malformed track-profile data.");
  return value;
}

export function parseSimulationResult(value: unknown): SimulationResult {
  if (!isRecord(value) || !isString(value.track) || value.track.length === 0
    || !isString(value.track_id) || value.track_id.length === 0
    || !isPositive(value.base_lap_time) || !isNonnegative(value.pit_loss) || !isPositive(value.degradation_multiplier)
    || !isPositiveInteger(value.total_generated) || !isPositiveInteger(value.deterministic_candidates_evaluated)
    || value.deterministic_candidates_evaluated > value.total_generated || !isPositiveInteger(value.simulations_per_strategy)
    || !["low", "medium", "high"].includes(String(value.confidence)) || !isNonnegative(value.win_gap_to_second)
    || !isString(value.recommendation) || !isProbability(value.safety_car_probability)
    || !isNonnegativeInteger(value.safety_car_simulations)
    || !isProbability(value.safety_car_rate) || !(value.seed === null || Number.isSafeInteger(value.seed))
    || !isStrategy(value.best_strategy) || !Array.isArray(value.ranked_strategies)
    || value.ranked_strategies.length === 0 || !value.ranked_strategies.every(isStrategy)) {
    throw new Error("The server returned malformed simulation data.");
  }
  const competitorIds = value.ranked_strategies.map((item) => item.strategy_id);
  if (value.safety_car_simulations > value.simulations_per_strategy
    || value.best_strategy.strategy_id !== value.ranked_strategies[0].strategy_id
    || value.ranked_strategies.length !== value.deterministic_candidates_evaluated
    || new Set(competitorIds).size !== competitorIds.length) {
    throw new Error("The server returned inconsistent simulation data.");
  }
  return value as unknown as SimulationResult;
}
