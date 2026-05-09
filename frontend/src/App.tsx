import { useState } from "react";
import { Activity, Flag, Gauge, Timer } from "lucide-react";

import Metric from "./components/Metric";
import Slider from "./components/Slider";
import StrategyRanking from "./components/StrategyRanking";
import RaceEngineerPanel from "./components/ai/RaceEngineerPanel";

import { getTrackProfile, runMonteCarloSimulation } from "./api/racebrain";
import type { SimulationInputs, SimulationResult } from "./types/racebrain";

export default function App() {
  const [track, setTrack] = useState("monaco");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);

  const [inputs, setInputs] = useState<SimulationInputs>({
    total_laps: 20,
    base_lap_time: 90,
    pit_loss: 22,
    simulations: 200,
  });

  async function handleTrackChange(trackId: string) {
    setTrack(trackId);

    const profile = await getTrackProfile(trackId);

    setInputs((current) => ({
      ...current,
      base_lap_time: profile.base_lap_time,
      pit_loss: profile.pit_loss,
    }));
  }

  async function handleRunSimulation() {
    setLoading(true);

    try {
      const data = await runMonteCarloSimulation(track, inputs);
      setResult(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen overflow-x-hidden text-white">
      <div className="absolute inset-0 opacity-30">
        <div className="absolute left-[-10%] top-16 h-72 w-72 rounded-full bg-red-600 blur-3xl" />
        <div className="absolute right-[-10%] top-40 h-96 w-96 rounded-full bg-indigo-500 blur-3xl" />
      </div>

     <div className="relative mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
        <nav className="mb-10 flex items-center justify-between rounded-3xl border border-white/10 bg-white/5 px-6 py-4 backdrop-blur-xl">
          <div>
            <p className="text-xs uppercase tracking-[0.45em] text-red-400">
              RaceBrain
            </p>
            <h1 className="text-2xl font-black tracking-tight">
              Pit Wall Intelligence
            </h1>
          </div>

          <div className="rounded-full border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm font-bold text-red-300">
            {track.toUpperCase()}
          </div>
        </nav>

       <section className="grid gap-6 lg:grid-cols-2">
          <div className="min-w-0 rounded-[2rem] border border-white/10 bg-black/40 p-8 shadow-2xl backdrop-blur-xl">
            <div className="mb-8 flex items-center gap-3">
              <Flag className="text-red-500" />
              <span className="text-sm uppercase tracking-[0.35em] text-white/50">
                Strategy Simulation Bay
              </span>
            </div>

            <h2 className="text-5xl font-black leading-none tracking-tight">
              Engineer the race.
              <span className="text-red-500"> Simulate the call.</span>
            </h2>

            <p className="mt-6 text-lg leading-8 text-white/60">
              Monte Carlo strategy simulation with tyre degradation, pit loss
              variance, candidate filtering, and win probability ranking.
            </p>

            <div className="mt-6">
              <p className="mb-2 text-xs uppercase tracking-[0.2em] text-white/40">
                Circuit
              </p>

              <select
                value={track}
                onChange={(e) => handleTrackChange(e.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-black/40 px-4 py-3 text-sm font-bold uppercase tracking-wider text-white outline-none"
              >
                <option value="monaco">Monaco</option>
                <option value="monza">Monza</option>
                <option value="silverstone">Silverstone</option>
                <option value="spa">Spa</option>
                <option value="suzuka">Suzuka</option>
              </select>
            </div>

            <div className="mt-8 grid grid-cols-2 gap-4">
              <Slider
                label="Total Laps"
                value={inputs.total_laps}
                min={10}
                max={100}
                step={1}
                onChange={(v) => setInputs({ ...inputs, total_laps: v })}
              />

              <Slider
                label="Base Lap Time"
                value={inputs.base_lap_time}
                min={60}
                max={130}
                step={0.5}
                suffix="s"
                onChange={(v) => setInputs({ ...inputs, base_lap_time: v })}
              />

              <Slider
                label="Pit Loss"
                value={inputs.pit_loss}
                min={15}
                max={35}
                step={0.5}
                suffix="s"
                onChange={(v) => setInputs({ ...inputs, pit_loss: v })}
              />

              <Slider
                label="Simulations"
                value={inputs.simulations}
                min={50}
                max={200}
                step={50}
                onChange={(v) => setInputs({ ...inputs, simulations: v })}
              />
            </div>

            <button
              onClick={handleRunSimulation}
              disabled={loading}
              className="mt-8 rounded-2xl bg-red-600 px-8 py-4 text-sm font-black uppercase tracking-[0.25em] text-white shadow-2xl shadow-red-600/30 transition hover:scale-[1.02] hover:bg-red-500 disabled:opacity-50"
            >
              {loading ? "Running simulation..." : "Run Strategy Model"}
            </button>

            {result && (
              <div className="mt-6 grid grid-cols-4 gap-3">
                <Metric
                  icon={<Timer />}
                  label="Base Lap"
                  value={`${result.base_lap_time}s`}
                />
                <Metric
                  icon={<Gauge />}
                  label="Pit Loss"
                  value={`${result.pit_loss}s`}
                />
                <Metric
                  icon={<Activity />}
                  label="Deg"
                  value={`${result.degradation_multiplier}x`}
                />
                <Metric
                  icon={<Flag />}
                  label="SC Rate"
                  value={`${(result.safety_car_rate * 100).toFixed(0)}%`}
                />
              </div>
            )}
            {result && (
              <StrategyRanking strategies={result.ranked_strategies} />
            )}
          </div>
<RaceEngineerPanel
  result={result}
  track={track}
  totalLaps={inputs.total_laps}
/>
        </section>
      </div>
    </main>
  );
}