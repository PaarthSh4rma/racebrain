import type { Strategy } from "../types/racebrain";
import { formatStrategy } from "../utils/formatStrategy";

export default function StrategyRanking({
  strategies,
}: {
  strategies: Strategy[];
}) {
  return (
    <div className="mt-6 rounded-[2rem] border border-white/10 bg-black/40 p-4 sm:p-6">
      <p className="mb-4 text-xs uppercase tracking-[0.3em] text-white/40">
        Strategy Ranking
      </p>

      <div className="space-y-3">
        {strategies.slice(0, 5).map((item) => (
          <div
            key={item.strategy_id}
            className="rounded-2xl border border-white/10 bg-white/5 p-4"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
              <div className="min-w-0">
                <p className="text-sm font-black text-white">
                  Strategy {item.strategy_id}
                </p>
                <p className="mt-1 break-words text-sm text-white/50">
                  {formatStrategy(item.strategy)}
                </p>
              </div>

              <div className="shrink-0 text-left sm:text-right">
                <p className="text-xl font-black text-red-400">
                  {item.win_percentage}%
                </p>
                <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                  win rate
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
