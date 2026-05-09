import { useState } from "react";
import type { SimulationResult } from "../types/racebrain";
import { formatStrategy } from "../utils/formatStrategy";

type ExplainResponse = {
  summary: string;
  recommendation_type: string;
  risk_level: string;
  key_factors: string[];
  tradeoffs: string[];
  pit_wall_call: string;
  follow_up_questions: string[];
  tools_used: string[];
};

export default function RaceEngineerChat({
  result,
}: {
  result: SimulationResult | null;
}) {
  const [message, setMessage] = useState("Why is this strategy best?");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ExplainResponse | null>(null);

  async function sendMessage() {
    if (!result) return;

    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/ai/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, simulation_result: result }),
      });

      const data = await res.json();
      setResponse(data);
    } finally {
      setLoading(false);
    }
  }

  const best = result?.best_strategy;

  return (
    <div className="rounded-[2rem] border border-white/10 bg-black/40 p-6 backdrop-blur-xl">
      <p className="text-xs uppercase tracking-[0.35em] text-cyan-400">
        Race Engineer AI
      </p>

      <h2 className="mt-2 text-3xl font-black">Strategy Analyst</h2>

      <p className="mt-3 text-white/50">
        Explains the currently displayed simulation result without rerunning
        Monte Carlo.
      </p>

      {!result || !best ? (
        <div className="mt-6 rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-4 text-yellow-200">
          Run the strategy model first to unlock AI analysis.
        </div>
      ) : (
        <>
          <div className="mt-6 rounded-2xl border border-red-500/20 bg-red-500/5 p-4">
            <p className="text-sm uppercase tracking-[0.2em] text-red-400">
              Recommended Call
            </p>

            <div className="mt-3 flex items-start justify-between gap-4">
              <div>
                <p className="text-3xl font-black">
                  Strategy {best.strategy_id}
                </p>

                <p className="mt-2 text-white/60">
                  {formatStrategy(best.strategy)}
                </p>
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

            <div className="mt-4 flex gap-3">
              <span className="rounded-full bg-white/10 px-3 py-1 text-sm">
                Confidence: {result.confidence}
              </span>

              <span className="rounded-full bg-white/10 px-3 py-1 text-sm">
                Gap: {result.win_gap_to_second}%
              </span>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm uppercase tracking-[0.2em] text-white/40">
              Model Signals
            </p>

            <ul className="mt-3 space-y-2 text-white/70">
              <li>• Safety car rate: {(result.safety_car_rate * 100).toFixed(0)}%</li>
              <li>• Simulations per strategy: {result.simulations_per_strategy}</li>
              <li>• Candidates evaluated: {result.deterministic_candidates_evaluated}</li>
            </ul>
          </div>

          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
            className="mt-4 w-full rounded-2xl border border-white/10 bg-black/40 p-4 text-white outline-none"
          />

          <button
            onClick={sendMessage}
            disabled={loading}
            className="mt-4 rounded-2xl bg-cyan-500 px-6 py-3 font-black text-black transition hover:scale-[1.02] disabled:opacity-50"
          >
            {loading ? "Analysing..." : "Ask Race Engineer"}
          </button>

{response && (
  <div className="mt-6 space-y-4">
    <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
      <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">
        Engineer Summary
      </p>
      <p className="mt-3 text-white/80">{response.summary}</p>
    </div>

    <div className="grid grid-cols-2 gap-3">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-white/40">
          Recommendation
        </p>
        <p className="mt-2 text-xl font-black capitalize">
          {response.recommendation_type}
        </p>
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-white/40">
          Risk
        </p>
        <p className="mt-2 text-xl font-black capitalize">
          {response.risk_level}
        </p>
      </div>
    </div>

    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-sm uppercase tracking-[0.2em] text-white/40">
        Key Factors
      </p>

      <ul className="mt-3 space-y-2 text-white/70">
        {response.key_factors.map((item, index) => (
          <li key={index}>• {item}</li>
        ))}
      </ul>
    </div>

    <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-4">
      <p className="text-sm uppercase tracking-[0.2em] text-red-400">
        Pit Wall Call
      </p>
      <p className="mt-3 text-white/80">{response.pit_wall_call}</p>
    </div>
  </div>
)}
        </>
      )}
    </div>
  );
}