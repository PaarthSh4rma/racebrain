import type { SimulationResult } from "../../types/racebrain";
import { formatStrategy } from "../../utils/formatStrategy";

export default function RecommendedStrategyCard({
  result,
}: {
  result: SimulationResult;
}) {
  const best = result.best_strategy;

  return (
    <div className="mt-6 rounded-2xl border border-red-500/20 bg-red-500/5 p-4">
      <p className="text-sm uppercase tracking-[0.2em] text-red-400">
        Recommended Call
      </p>

      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="min-w-0">
          <p className="break-words text-2xl font-black sm:text-3xl">Strategy {best.strategy_id}</p>
          <p className="mt-2 break-words text-white/60">{formatStrategy(best.strategy)}</p>
        </div>

        <div className="shrink-0 text-left sm:text-right">
          <p className="text-3xl font-black text-red-400">
            {best.preference_percentage}%
          </p>
          <p className="text-xs uppercase tracking-[0.2em] text-white/40">
            scenario preference
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <span className="rounded-full bg-white/10 px-3 py-1 text-sm">
          Confidence: {result.confidence}
        </span>

        <span className="rounded-full bg-white/10 px-3 py-1 text-sm">
          Preference gap: {result.win_gap_to_second} pts
        </span>

        <span className="rounded-full bg-white/10 px-3 py-1 text-sm">
          SC: {(result.safety_car_rate * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}
