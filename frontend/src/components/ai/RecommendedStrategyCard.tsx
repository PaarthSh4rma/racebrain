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

      <div className="mt-3 flex items-start justify-between gap-4">
        <div>
          <p className="text-3xl font-black">Strategy {best.strategy_id}</p>
          <p className="mt-2 text-white/60">{formatStrategy(best.strategy)}</p>
        </div>

        <div className="text-right">
          <p className="text-3xl font-black text-red-400">
            {best.win_percentage}%
          </p>
          <p className="text-xs uppercase tracking-[0.2em] text-white/40">
            win rate
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <span className="rounded-full bg-white/10 px-3 py-1 text-sm">
          Confidence: {result.confidence}
        </span>

        <span className="rounded-full bg-white/10 px-3 py-1 text-sm">
          Gap: {result.win_gap_to_second}%
        </span>

        <span className="rounded-full bg-white/10 px-3 py-1 text-sm">
          SC: {(result.safety_car_rate * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}