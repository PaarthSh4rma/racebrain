import type { SimulationInputs, SimulationResult, Strategy } from "../../types/racebrain";
import { formatStrategy } from "../../utils/formatStrategy";
import { SCENARIO_SIMULATION_CONFIG } from "../../api/racebrain";

function formatRaceTime(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = seconds % 60;
  return `${hours}:${String(minutes).padStart(2, "0")}:${remaining.toFixed(3).padStart(6, "0")}`;
}

function StrategyRow({ item, rank }: { item: Strategy; rank: number }) {
  return (
    <tr className="border-t border-slate-800">
      <td className="px-3 py-3 font-mono text-slate-500">{String(rank).padStart(2, "0")}</td>
      <td className="min-w-[250px] px-3 py-3"><p className="font-medium text-slate-100">Strategy {item.strategy_id}</p><p className="mt-1 font-mono text-xs text-slate-400">{formatStrategy(item.strategy)}</p></td>
      <td className="px-3 py-3 font-mono text-cyan-300">{item.preference_percentage.toFixed(2)}%</td>
      <td className="px-3 py-3 font-mono text-slate-200">{formatRaceTime(item.average_total_time)}</td>
      <td className="px-3 py-3 font-mono text-slate-400">±{item.std_dev.toFixed(3)} s</td>
    </tr>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="border-r border-slate-700 px-3 py-3 last:border-r-0"><dt className="text-[10px] uppercase tracking-wider text-slate-500">{label}</dt><dd className="mt-1 font-mono text-sm text-slate-100">{children}</dd></div>;
}

export default function SimulationResults({ result, inputs }: { result: SimulationResult; inputs: SimulationInputs }) {
  const best = result.best_strategy;
  return (
    <div className="space-y-4" data-testid="simulation-results">
      <section className="border border-slate-700 bg-slate-900" aria-labelledby="scenario-summary-heading">
        <header className="border-b border-slate-700 px-4 py-3"><p className="text-[10px] uppercase tracking-[0.2em] text-cyan-400">Scenario summary</p><h2 id="scenario-summary-heading" className="mt-1 text-lg font-semibold">{result.track}</h2></header>
        <dl className="grid grid-cols-2 divide-y divide-slate-700 sm:grid-cols-4 sm:divide-y-0">
          <Fact label="Total laps">{inputs.total_laps}</Fact><Fact label="Base lap">{result.base_lap_time.toFixed(1)} s</Fact><Fact label="Pit loss">{result.pit_loss.toFixed(1)} s</Fact><Fact label="Runs / strategy">{result.simulations_per_strategy}</Fact>
          <Fact label="Generated strategies">{result.total_generated}</Fact><Fact label="Candidates evaluated">{result.deterministic_candidates_evaluated}</Fact><Fact label="Simulation seed">{result.seed ?? "random"}</Fact><Fact label="Safety-car samples">{result.safety_car_simulations}</Fact>
        </dl>
      </section>

      <section className="grid gap-px border border-slate-700 bg-slate-700 lg:grid-cols-[1.25fr_0.75fr]" aria-labelledby="best-strategy-heading">
        <article className="bg-slate-950 p-5"><p className="text-[10px] uppercase tracking-[0.2em] text-cyan-400">Best-ranked strategy</p><h2 id="best-strategy-heading" className="mt-2 text-xl font-semibold">Strategy {best.strategy_id}</h2><p className="mt-3 font-mono text-sm leading-6 text-slate-300">{formatStrategy(best.strategy)}</p><p className="mt-4 text-xs leading-5 text-slate-500">Best-ranked means fastest most often among these generated candidates under the sampled simulator conditions. It is not a probability of winning a real race.</p></article>
        <dl className="grid grid-cols-2 gap-px bg-slate-700"><div className="bg-slate-950 p-4"><dt className="text-[10px] uppercase tracking-wider text-slate-500">Scenario preference</dt><dd className="mt-2 font-mono text-2xl font-semibold text-cyan-300">{best.preference_percentage.toFixed(2)}%</dd><p className="mt-1 text-xs text-slate-500">Fastest in sampled scenarios</p></div><div className="bg-slate-950 p-4"><dt className="text-[10px] uppercase tracking-wider text-slate-500">Top-two preference gap</dt><dd className="mt-2 font-mono text-2xl font-semibold text-slate-100">{result.win_gap_to_second.toFixed(2)} pp</dd></div><div className="bg-slate-950 p-4"><dt className="text-[10px] uppercase tracking-wider text-slate-500">Average simulated race time</dt><dd className="mt-2 font-mono text-lg text-slate-100">{formatRaceTime(best.average_total_time)}</dd></div><div className="bg-slate-950 p-4"><dt className="text-[10px] uppercase tracking-wider text-slate-500">Scenario spread</dt><dd className="mt-2 font-mono text-lg text-slate-100">±{best.std_dev.toFixed(3)} s</dd></div></dl>
      </section>

      <section className="overflow-hidden border border-slate-700 bg-slate-900" aria-labelledby="ranked-heading">
        <header className="border-b border-slate-700 px-4 py-3"><h2 id="ranked-heading" className="text-sm font-semibold uppercase tracking-[0.16em]">Ranked strategies</h2><p className="mt-1 text-xs text-slate-500">Preference is the frequency each candidate was fastest within the sampled comparison set.</p></header>
        <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-slate-950 text-[10px] uppercase tracking-wider text-slate-500"><tr><th className="px-3 py-2">Rank</th><th className="px-3 py-2">Candidate</th><th className="px-3 py-2">Scenario preference</th><th className="px-3 py-2">Average time</th><th className="px-3 py-2">Spread</th></tr></thead><tbody>{result.ranked_strategies.slice(0, SCENARIO_SIMULATION_CONFIG.maximumEvaluatedCandidates).map((item, index) => <StrategyRow key={item.strategy_id} item={item} rank={index + 1} />)}</tbody></table></div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="border border-slate-700 bg-slate-900 p-4"><h2 className="text-sm font-semibold uppercase tracking-[0.16em]">Simulation assumptions</h2><dl className="mt-4 grid grid-cols-2 gap-4 text-sm"><div><dt className="text-xs text-slate-500">Lap-time variance</dt><dd className="mt-1 font-mono">{SCENARIO_SIMULATION_CONFIG.lapVariance.toFixed(2)} s</dd></div><div><dt className="text-xs text-slate-500">Pit-loss variance</dt><dd className="mt-1 font-mono">{SCENARIO_SIMULATION_CONFIG.pitVariance.toFixed(2)} s</dd></div><div><dt className="text-xs text-slate-500">Track multiplier</dt><dd className="mt-1 font-mono">{result.degradation_multiplier.toFixed(2)}×</dd></div><div><dt className="text-xs text-slate-500">Safety-car profile</dt><dd className="mt-1 font-mono">{(result.safety_car_probability * 100).toFixed(0)}% configured · {(result.safety_car_rate * 100).toFixed(1)}% sampled</dd></div></dl><p className="mt-4 text-xs leading-5 text-slate-500">One-stop and two-stop candidates are generated, deterministically pre-ranked, then the top bounded set is compared under paired Monte Carlo conditions.</p></article>
        <article className="border border-slate-700 bg-slate-900 p-4"><h2 className="text-sm font-semibold uppercase tracking-[0.16em]">Limitations</h2><ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-5 text-slate-400"><li>Exploratory simulator; not the V2 historical decision engine.</li><li>Not connected to canonical historical RaceState evidence.</li><li>No live traffic, dirty-air or real opponent behaviour model.</li><li>No V2 strategy recommendation, pit-window or rejoin semantics.</li><li>Scenario preference is candidate-comparison frequency, not race-win probability.</li></ul></article>
      </section>
    </div>
  );
}
