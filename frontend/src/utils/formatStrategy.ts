import type { Stint } from "../types/racebrain";

export function formatStrategy(strategy: Stint[]) {
  return strategy
    .map((stint) => `${stint.compound.toUpperCase()} ${stint.laps}`)
    .join(" → ");
}