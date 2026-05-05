import { useState } from "react";
import {
  Trophy,
  Gauge,
  Timer,
  Activity,
  Flag,
  Zap,
  BarChart3,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

type Strategy = {
  strategy_id: number;
  strategy: { compound: string; laps: number }[];
  win_percentage: number;
  average_total_time: number;
  std_dev: number;
};

type ApiResponse = {
  total_generated: number;
  deterministic_candidates_evaluated: number;
  simulations_per_strategy: number;
  confidence: string;
  win_gap_to_second: number;
  recommendation: string;
  best_strategy: Strategy;
  ranked_strategies: Strategy[];
};

const API_URL = "http://127.0.0.1:8000";

function formatStrategy(strategy: Strategy["strategy"]) {
  return strategy
    .map((stint) => `${stint.compound.toUpperCase()} ${stint.laps}`)
    .join(" → ");
}


export default function App() {
  const [result, setResult] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [track, setTrack] = useState("monaco");
  

  const [inputs, setInputs] = useState({
    total_laps: 20,
    base_lap_time: 90,
    pit_loss: 22,
    simulations: 200,
  });
async function loadTrackProfile(trackId: string) {
  const response = await fetch(`${API_URL}/tracks/${trackId}`);
  const profile = await response.json();

  setInputs((current) => ({
    ...current,
    base_lap_time: profile.base_lap_time,
    pit_loss: profile.pit_loss,
  }));
}

  async function runSimulation() {
    setLoading(true);

    const response = await fetch(`${API_URL}/monte-carlo/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
        body: JSON.stringify({
          track,
          total_laps: inputs.total_laps,
          simulations: inputs.simulations,
          lap_variance: 0.35,
          pit_variance: 1.5,
          include_one_stop: true,
          include_two_stop: false,
        }),
    });

    const data = await response.json();
    setResult(data);
    setLoading(false);
  }

  const chartData =
    result?.ranked_strategies.map((item) => ({
      name: `S${item.strategy_id}`,
      win: item.win_percentage,
      time: item.average_total_time,
    })) ?? [];

  return (
    <main className="min-h-screen overflow-hidden text-white">
      <div className="absolute inset-0 opacity-30">
        <div className="absolute left-[-10%] top-16 h-72 w-72 rounded-full bg-red-600 blur-3xl" />
        <div className="absolute right-[-10%] top-40 h-96 w-96 rounded-full bg-indigo-500 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6 py-8">
        <nav className="mb-10 flex items-center justify-between rounded-3xl border border-white/10 bg-white/5 px-6 py-4 backdrop-blur-xl">
          <div>
            <p className="text-xs uppercase tracking-[0.45em] text-red-400">
              RaceBrain
            </p>
            <h1 className="text-2xl font-black tracking-tight">
              Pit Wall Intelligence
            </h1>
          </div>

          <div className="hidden gap-8 text-sm text-white/60 md:flex">
            <span>Strategy Lab</span>
            <span>Telemetry</span>
            <span>Race Control</span>
          </div>

          <div className="rounded-full border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm font-bold text-red-300">
            {track.toUpperCase()}
          </div>
        </nav>

        <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[2rem] border border-white/10 bg-black/40 p-8 shadow-2xl backdrop-blur-xl">
            <div className="mb-8 flex items-center gap-3">
              <Flag className="text-red-500" />
              <span className="text-sm uppercase tracking-[0.35em] text-white/50">
                Monaco Simulation Bay
              </span>
            </div>

            <h2 className="max-w-3xl text-6xl font-black leading-none tracking-tight">
              Enter the paddock.{" "}
              <span className="text-red-500">Engineer the race.</span>
            </h2>

            <p className="mt-6 max-w-2xl text-lg leading-8 text-white/60">
              Monte Carlo strategy simulation with tyre degradation, pit loss
              variance, candidate filtering, and win probability ranking.
            </p>

            <button
              onClick={runSimulation}
              disabled={loading}
              className="mt-8 rounded-2xl bg-red-600 px-8 py-4 text-sm font-black uppercase tracking-[0.25em] text-white shadow-2xl shadow-red-600/30 transition hover:scale-[1.02] hover:bg-red-500 disabled:opacity-50"
            >
              {loading ? "Running simulation..." : "Run Strategy Model"}
            </button>

            <div className="mt-6">
              <p className="mb-2 text-xs uppercase tracking-[0.2em] text-white/40">
                Circuit
              </p>

              <div className="relative">
                <select
                  value={track}
                  onChange={(e) => {
                    const selectedTrack = e.target.value;
                    setTrack(selectedTrack);
                    loadTrackProfile(selectedTrack);
                  }}
                  className="w-full appearance-none rounded-2xl border border-white/10 bg-black/40 px-4 py-3 text-sm font-bold uppercase tracking-wider text-white outline-none"
                >
                  <option value="monaco">Monaco</option>
                  <option value="monza">Monza</option>
                  <option value="silverstone">Silverstone</option>
                  <option value="spa">Spa</option>
                  <option value="suzuka">Suzuka</option>
                </select>

                <div className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-white/40">
                  ▼
                </div>
              </div>
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
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
            <p className="mb-6 text-sm uppercase tracking-[0.35em] text-white/50">
              Recommended Call
            </p>

            {result ? (
              <>
                <div className="rounded-3xl bg-black/50 p-6">
                  <Trophy className="mb-4 text-yellow-300" />
                  <p className="text-sm text-white/50">Best Strategy</p>
                  <h3 className="mt-2 text-3xl font-black">
                    {formatStrategy(result.best_strategy.strategy)}
                  </h3>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-3">
                  <Metric
                    icon={<Zap />}
                    label="Win %"
                    value={`${result.best_strategy.win_percentage}%`}
                  />
                  <Metric
                    icon={<Gauge />}
                    label="Confidence"
                    value={result.confidence.toUpperCase()}
                  />
                  <Metric
                    icon={<Timer />}
                    label="Gap"
                    value={`${result.win_gap_to_second}%`}
                  />
                </div>

                <p className="mt-5 rounded-3xl border border-white/10 bg-black/40 p-5 text-sm leading-7 text-white/70">
                  {result.recommendation}
                </p>
              </>
            ) : (
              <div className="flex h-80 items-center justify-center rounded-3xl border border-dashed border-white/15 text-white/40">
                Awaiting pit wall command
              </div>
            )}
          </div>
        </section>

        {result && (
          <section className="mt-6 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
              <div className="mb-6 flex items-center gap-3">
                <BarChart3 className="text-red-400" />
                <h3 className="text-xl font-black">Win Probability</h3>
              </div>

              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <XAxis dataKey="name" stroke="#ffffff55" />
                    <YAxis stroke="#ffffff55" />
                    <Tooltip
                      contentStyle={{
                        background: "#09090b",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: "16px",
                        color: "#fff",
                      }}
                    />
                    <Bar dataKey="win" radius={[10, 10, 0, 0]}>
                      {chartData.map((_, index) => (
                        <Cell
                          key={index}
                          fill={index === 0 ? "#ef4444" : "#71717a"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-black/40 p-6 backdrop-blur-xl">
              <div className="mb-6 flex items-center gap-3">
                <Activity className="text-red-400" />
                <h3 className="text-xl font-black">Strategy Ranking</h3>
              </div>

              <div className="space-y-3">
                {result.ranked_strategies.map((item, index) => (
                  <div
                    key={item.strategy_id}
                    className="grid grid-cols-[40px_1fr_90px_110px_90px] items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4"
                  >
                    <span className="text-white/40">#{index + 1}</span>
                    <span className="font-bold">
                      {formatStrategy(item.strategy)}
                    </span>
                    <span className="text-red-300">{item.win_percentage}%</span>
                    <span className="text-white/60">
                      {item.average_total_time}s
                    </span>
                    <span className="text-white/60">±{item.std_dev}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}
      </div>

      <footer className="relative mx-auto mt-10 max-w-7xl px-6 pb-8 text-center text-xs leading-6 text-white/35">
  RaceBrain is an independent fan-made strategy simulation project.
  It is not affiliated with, endorsed by, or connected to Formula 1,
  Formula One Management, Liberty Media, the FIA, or any Formula 1 team.
  Formula 1, F1, and related marks belong to their respective owners. 
  I love technology, AI and Formula One... and thought of making something that combines them!
</footer>
    </main>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/40 p-4">
      <div className="mb-3 text-red-400">{icon}</div>
      <p className="text-xs uppercase tracking-[0.2em] text-white/40">
        {label}
      </p>
      <p className="mt-2 text-lg font-black">{value}</p>
    </div>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  suffix = "",
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix?: string;
  onChange: (v: number) => void;
}) {
  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div className="rounded-2xl border border-white/10 bg-black/40 p-4">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs uppercase tracking-[0.2em] text-white/40">
          {label}
        </p>
        <p className="rounded-full bg-red-500/10 px-3 py-1 text-sm font-black text-red-300">
          {value}
          {suffix}
        </p>
      </div>

      <div className="relative">
        <div className="absolute left-0 top-1/2 h-2 w-full -translate-y-1/2 rounded-full bg-white/10" />
        <div
          className="absolute left-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-red-500"
          style={{ width: `${percentage}%` }}
        />

        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="relative z-10 w-full cursor-pointer appearance-none bg-transparent accent-red-500"
        />
      </div>
    </div>
  );
}