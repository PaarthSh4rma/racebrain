import type { ScenarioResponse } from "../../types/ai";

export default function ScenarioResultCard({
  scenario,
}: {
  scenario: ScenarioResponse;
}) {
  if (!scenario.comparison) {
    return (
      <div className="mt-6 rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-yellow-400">
          Scenario Not Detected
        </p>
        <p className="mt-3 text-white/80">{scenario.summary}</p>
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-4">
      <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-yellow-400">
          Scenario Simulation
        </p>
        <p className="mt-3 text-white/80">{scenario.summary}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <p className="text-sm uppercase tracking-[0.2em] text-white/40">
            Original
          </p>
          <p className="mt-2 text-3xl font-black">
            Strategy {scenario.comparison.original_strategy}
          </p>
          <p className="mt-2 text-white/60">
            {scenario.comparison.original_win_rate}% win rate
          </p>
        </div>

        <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">
            Scenario Result
          </p>
          <p className="mt-2 text-3xl font-black">
            Strategy {scenario.comparison.new_strategy}
          </p>
          <p className="mt-2 text-white/60">
            {scenario.comparison.new_win_rate}% win rate
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-white/40">
          Applied Adjustments
        </p>

        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(scenario.adjustments || {}).map(([key, value]) => (
            <span
              key={key}
              className="rounded-full bg-white/10 px-3 py-1 text-sm text-white/70"
            >
              {key}: {String(value)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}