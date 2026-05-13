import type { LiveStrategyResponse } from "../../types/raceData";

export default function LiveStrategyCallCard({
  data,
}: {
  data: LiveStrategyResponse;
}) {
  const call = data.strategy_call;

  return (
    <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-5">
      <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">
        Live Strategy Call
      </p>

      <h3 className="mt-3 text-3xl font-black capitalize text-white">
        {call.recommendation.replaceAll("_", " ")}
      </h3>

      <p className="mt-3 text-white/75">{call.call}</p>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-black/30 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-white/40">
            Tyre Risk
          </p>
          <p className="mt-1 text-lg font-black capitalize">
            {call.tyre_risk}
          </p>
        </div>

        <div className="rounded-xl bg-black/30 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-white/40">
            Volatility
          </p>
          <p className="mt-1 text-lg font-black capitalize">
            {call.race_volatility}
          </p>
        </div>
      </div>

      {call.current_stint && (
        <div className="mt-4 rounded-xl border border-white/10 bg-black/30 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-white/40">
            Current Stint
          </p>

          <p className="mt-2 text-white/80">
            {call.current_stint.compound} · Lap {call.current_stint.lap_start}–
            {call.current_stint.lap_end}
          </p>
        </div>
      )}

      <ul className="mt-4 space-y-2 text-white/70">
        {call.reasoning.map((item, index) => (
          <li key={index}>• {item}</li>
        ))}
      </ul>
    </div>
  );
}