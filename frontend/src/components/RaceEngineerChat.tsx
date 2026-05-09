import { useState } from "react";
import type { SimulationResult } from "../types/racebrain";
import { formatStrategy } from "../utils/formatStrategy";
import ReactMarkdown from "react-markdown";

type ExplainResponse = {
  summary?: string;
  response?: string;
  recommendation_type?: string;
  risk_level?: string;
  key_factors?: string[];
  tradeoffs?: string[];
  pit_wall_call?: string;
  follow_up_questions?: string[];
  tools_used?: string[];
  answer_type?: string;
  points?: string[];
  analysis_used?: string;
};

function isScenarioQuestion(message: string) {
  const lowered = message.toLowerCase();

  return (
    lowered.includes("what if") ||
    lowered.includes("increase") ||
    lowered.includes("decrease") ||
    lowered.includes("higher") ||
    lowered.includes("lower") ||
    lowered.includes("one-stop") ||
    lowered.includes("one stop")
  );
}
type ScenarioResponse = {
  summary: string;
  adjustments: Record<string, unknown>;
  comparison: {
    original_strategy: number;
    new_strategy: number;
    original_win_rate: number;
    new_win_rate: number;
    strategy_changed: boolean;
  };
  modified_result: SimulationResult;
};

export default function RaceEngineerChat({
  result,
  totalLaps,
}: {
  result: SimulationResult | null;
  totalLaps: number;
}) {
  const [message, setMessage] = useState("Why is this strategy best?");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ExplainResponse | null>(null);
  const [useLlm, setUseLlm] = useState(false);
  const [scenarioResponse, setScenarioResponse] = useState<ScenarioResponse | null>(null);

    async function sendMessage() {
    setScenarioResponse(null);
    if (!result) return;

    setLoading(true);

    try {
        const scenarioKeywords = [
  "degradation",
  "safety car",
  "one-stop",
  "one stop",
  "increase",
  "decrease",
  "higher",
  "lower",
];

const isScenario =
  message.toLowerCase().includes("what if") &&
  scenarioKeywords.some((keyword) =>
    message.toLowerCase().includes(keyword)
  );

if (isScenario) {
        const res = await fetch(
            "http://127.0.0.1:8000/ai/scenario",
            {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                question: message,
                track: result.track,
                total_laps: totalLaps,
                simulations: result.simulations_per_strategy,
                original_result: result,
            }),
            }
        );

        const data = await res.json();

        setScenarioResponse(data);
        setResponse(null);

        setLoading(false);
        return;
        }
        const endpoint = useLlm
        ? "http://127.0.0.1:8000/ai/llm-explain"
        : "http://127.0.0.1:8000/ai/explain";

        const body = useLlm
        ? {
            question: message,
            simulation_result: result,
            }
        : {
            message,
            simulation_result: result,
            };

        const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
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

          <div className="mt-4 flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-4">
            <div>
                <p className="text-sm font-black text-white">LLM Mode</p>
                <p className="text-sm text-white/50">
                Uses grounded OpenRouter response instead of deterministic analysis only.
                </p>
            </div>

            <button
                onClick={() => setUseLlm((current) => !current)}
                className={`rounded-full px-4 py-2 text-sm font-black transition ${
                useLlm
                    ? "bg-cyan-500 text-black"
                    : "bg-white/10 text-white/60"
                }`}
            >
                {useLlm ? "ON" : "OFF"}
            </button>
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

{scenarioResponse && !scenarioResponse.comparison && (
  <div className="mt-6 rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-4">
    <p className="text-sm uppercase tracking-[0.2em] text-yellow-400">
      Scenario Not Detected
    </p>

    <p className="mt-3 text-white/80">
      {scenarioResponse.summary}
    </p>
  </div>
)}

{scenarioResponse?.comparison && (
  <div className="mt-6 space-y-4">
    <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-4">
      <p className="text-sm uppercase tracking-[0.2em] text-yellow-400">
        Scenario Simulation
      </p>

      <p className="mt-3 text-white/80">
        {scenarioResponse.summary}
      </p>
    </div>

    <div className="grid grid-cols-2 gap-4">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-white/40">
          Original
        </p>

        <p className="mt-2 text-3xl font-black">
          Strategy {scenarioResponse?.comparison.original_strategy}
        </p>

        <p className="mt-2 text-white/60">
          {scenarioResponse?.comparison.original_win_rate}% win rate
        </p>
      </div>

      <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">
          Scenario Result
        </p>

        <p className="mt-2 text-3xl font-black">
          Strategy {scenarioResponse?.comparison.new_strategy}
        </p>

        <p className="mt-2 text-white/60">
          {scenarioResponse?.comparison.new_win_rate}% win rate
        </p>
      </div>
    </div>

    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-sm uppercase tracking-[0.2em] text-white/40">
        Applied Adjustments
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        {Object.entries(scenarioResponse.adjustments || {}).map(
          ([key, value]) => (
            <span
              key={key}
              className="rounded-full bg-white/10 px-3 py-1 text-sm"
            >
              {key}: {String(value)}
            </span>
          )
        )}
      </div>
    </div>
  </div>
)}
{response && (
  <div className="mt-6 space-y-4">
    <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
      <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">
        Engineer Summary
      </p>
        <div className="prose prose-invert mt-3 max-w-none prose-p:text-white/80 prose-strong:text-cyan-300">
        <ReactMarkdown>
            {response.response ?? response.summary ?? ""}
        </ReactMarkdown>
        </div>
    </div>

    {response.points && response.points.length > 0 && (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-white/40">
          Analysis
        </p>

        <ul className="mt-3 space-y-2 text-white/70">
          {response.points.map((item, index) => (
            <li key={index}>• {item}</li>
          ))}
        </ul>
      </div>
    )}

    {(response.recommendation_type || response.risk_level) && (
      <div className="grid grid-cols-2 gap-3">
        {response.recommendation_type && (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm uppercase tracking-[0.2em] text-white/40">
              Recommendation
            </p>
            <p className="mt-2 text-xl font-black capitalize">
              {response.recommendation_type}
            </p>
          </div>
        )}

        {response.risk_level && (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm uppercase tracking-[0.2em] text-white/40">
              Risk
            </p>
            <p className="mt-2 text-xl font-black capitalize">
              {response.risk_level}
            </p>
          </div>
        )}
      </div>
    )}

    {response.key_factors && response.key_factors.length > 0 && (
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
    )}

    {response.tradeoffs && response.tradeoffs.length > 0 && (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-white/40">
          Tradeoffs
        </p>

        <ul className="mt-3 space-y-2 text-white/70">
          {response.tradeoffs.map((item, index) => (
            <li key={index}>• {item}</li>
          ))}
        </ul>
      </div>
    )}

    {response.pit_wall_call && (
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-red-400">
          Pit Wall Call
        </p>
        <p className="mt-3 text-white/80">{response.pit_wall_call}</p>
      </div>
    )}

    {response.analysis_used && (
    <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">
        Analysis Used
        </p>
        <p className="mt-2 text-white/80">{response.analysis_used}</p>
    </div>
    )}

    {response.tools_used && response.tools_used.length > 0 && (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-white/40">
          Tools Used
        </p>

        <div className="mt-3 flex flex-wrap gap-2">
          {response.tools_used.map((tool) => (
            <span
              key={tool}
              className="rounded-full bg-white/10 px-3 py-1 text-sm text-white/70"
            >
              {tool}
            </span>
          ))}
        </div>
      </div>
    )}
  </div>
)}
        </>
      )}
    </div>
  );
}