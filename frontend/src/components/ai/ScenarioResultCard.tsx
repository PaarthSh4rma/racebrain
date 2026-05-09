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

      {scenario.agent_steps && scenario.agent_steps.length > 0 && (
  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
    <p className="text-sm uppercase tracking-[0.2em] text-white/40">
      Agent Steps
    </p>

    <ol className="mt-3 list-decimal space-y-2 pl-5 text-white/70">
      {scenario.agent_steps.map((step, index) => (
        <li key={index}>{step}</li>
      ))}
    </ol>
  </div>
)}

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

      {scenario.comparison.win_rate_delta !== undefined && (
  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
    <p className="text-sm uppercase tracking-[0.2em] text-white/40">
      Delta
    </p>

    <p className="mt-2 text-2xl font-black">
      {scenario.comparison.win_rate_delta > 0 ? "+" : ""}
      {scenario.comparison.win_rate_delta}% win rate
    </p>

    <p className="mt-2 text-white/50">
      Confidence: {scenario.comparison.original_confidence ?? "unknown"} →{" "}
      {scenario.comparison.new_confidence ?? "unknown"}
    </p>
  </div>
)}

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
      {scenario.contingency && scenario.contingency.length > 0 && (
  <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-4">
    <p className="text-sm uppercase tracking-[0.2em] text-red-400">
      Contingency Guidance
    </p>

    <ul className="mt-3 space-y-2 text-white/75">
      {scenario.contingency.map((item, index) => (
        <li key={index}>• {item}</li>
      ))}
    </ul>
  </div>
)}
    </div>
  );
}