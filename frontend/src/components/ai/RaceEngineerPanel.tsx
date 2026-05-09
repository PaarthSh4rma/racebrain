import { useState } from "react";

import type { AiResponse, ScenarioResponse } from "../../types/ai";
import type { SimulationResult } from "../../types/racebrain";

import {
  explainSimulation,
  explainSimulationWithLlm,
  runScenarioSimulation,
} from "../../api/ai";

import AiModeToggle from "./AiModeToggle";
import AiResponseCard from "./AiResponseCard";
import RecommendedStrategyCard from "./RecommendedStrategyCard";
import ScenarioResultCard from "./ScenarioResultCard";

function isScenarioQuestion(message: string) {
  const lowered = message.toLowerCase();

  const scenarioKeywords = [
    "degradation",
    "safety car",
    "one-stop",
    "one stop",
    "increase",
    "decrease",
    "higher",
    "lower",
    "rain",
    "rains",
    "wet",
    "storm",
    "ferrari",
    "push",
    "attack",
    "conservative",
    "save tyres",
  ];

  return (
    lowered.includes("what if") &&
    scenarioKeywords.some((keyword) => lowered.includes(keyword))
  );
}

export default function RaceEngineerPanel({
  result,
  track,
  totalLaps,
}: {
  result: SimulationResult | null;
  track: string;
  totalLaps: number;
}) {
  const [message, setMessage] = useState("Why is this strategy best?");
  const [useLlm, setUseLlm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState<AiResponse | null>(null);
  const [scenarioResponse, setScenarioResponse] =
    useState<ScenarioResponse | null>(null);

  async function sendMessage() {
    if (!result) return;

    setLoading(true);
    setAiResponse(null);
    setScenarioResponse(null);

    try {
      if (isScenarioQuestion(message)) {
        const data = await runScenarioSimulation({
          message,
          track,
          totalLaps,
          simulations: result.simulations_per_strategy,
          result,
        });

        setScenarioResponse(data);
        return;
      }

      const data = useLlm
        ? await explainSimulationWithLlm(message, result)
        : await explainSimulation(message, result);

      setAiResponse(data);
    } catch (error) {
      setAiResponse({
        summary: "Race Engineer failed to process that request.",
        points: [String(error)],
        tools_used: ["frontend_error_handler"],
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-w-0 rounded-[2rem] border border-white/10 bg-black/40 p-6 backdrop-blur-xl">
      <p className="text-xs uppercase tracking-[0.35em] text-cyan-400">
        Race Engineer AI
      </p>

      <h2 className="mt-2 text-3xl font-black">Strategy Analyst</h2>

      <p className="mt-3 text-white/50">
        Explains the current simulation, answers strategy questions, and reruns
        scenario changes.
      </p>

      {!result ? (
        <div className="mt-6 rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-4 text-yellow-200">
          Run the strategy model first to unlock AI analysis.
        </div>
      ) : (
        <>
          <RecommendedStrategyCard result={result} />

          <AiModeToggle useLlm={useLlm} onToggle={() => setUseLlm((v) => !v)} />

          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
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

          {scenarioResponse && <ScenarioResultCard scenario={scenarioResponse} />}
          {aiResponse && <AiResponseCard response={aiResponse} />}
        </>
      )}
    </div>
  );
}