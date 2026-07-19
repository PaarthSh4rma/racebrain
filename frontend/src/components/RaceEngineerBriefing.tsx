import { useState } from "react";
import { API_URL, apiError } from "../api/config";

type BriefingResponse = {
  track: string;
  recommendation: {
    strategy_text: string;
    win_percentage: number;
    confidence: string;
    summary: string;
  };
  race_engineer_briefing: {
    decision: string;
    reasoning: string[];
    risks: string[];
  };
};

export default function RaceEngineerBriefing({
  track,
  totalLaps,
}: {
  track: string;
  totalLaps: number;
}) {
  const [loading, setLoading] = useState(false);
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function generateBriefing() {
    setLoading(true);
    setError(null);
    setBriefing(null);

    try {
      const response = await fetch(
        `${API_URL}/race-engineer/briefing`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        body: JSON.stringify({
        track,
        total_laps: totalLaps,
        simulations: 200,
        }),
        }
      );

      if (!response.ok) throw await apiError(response, "Failed to generate briefing.");

      const data = await response.json();
      setBriefing(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate briefing.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">
            Race Engineer AI
          </h2>

          <p className="text-zinc-400 mt-1">
            Autonomous strategy recommendation system
          </p>
        </div>

        <button
          onClick={generateBriefing}
          disabled={loading}
          className="rounded-xl bg-red-600 px-4 py-2 font-semibold text-white hover:bg-red-500 transition"
        >
          {loading ? "Simulating..." : "Generate Briefing"}
        </button>
      </div>

      {!briefing && (
        <div className="text-zinc-500">
          No strategy briefing generated yet.
        </div>
      )}

      {error && <div className="mt-4 text-red-300">{error}</div>}

      {briefing && (
        <div className="space-y-6">
          <div className="rounded-xl bg-zinc-900 p-4 border border-zinc-800">
            <div className="text-sm uppercase tracking-wide text-red-400 mb-2">
              Recommendation
            </div>

            <div className="text-xl font-bold text-white">
              {briefing.race_engineer_briefing.decision}
            </div>

            <div className="mt-2 text-zinc-300">
              {briefing.recommendation.strategy_text}
            </div>

            <div className="mt-4 flex gap-4">
              <div className="rounded-lg bg-zinc-800 px-3 py-2">
                <div className="text-xs text-zinc-400">Win Rate</div>
                <div className="text-lg font-bold text-white">
                  {briefing.recommendation.win_percentage}%
                </div>
              </div>

              <div className="rounded-lg bg-zinc-800 px-3 py-2">
                <div className="text-xs text-zinc-400">Confidence</div>
                <div className="text-lg font-bold capitalize text-white">
                  {briefing.recommendation.confidence}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-zinc-900 p-4 border border-zinc-800">
            <div className="text-sm uppercase tracking-wide text-blue-400 mb-3">
              AI Reasoning
            </div>

            <ul className="space-y-2">
              {briefing.race_engineer_briefing.reasoning.map((reason, idx) => (
                <li key={idx} className="text-zinc-300">
                  • {reason}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl bg-zinc-900 p-4 border border-zinc-800">
            <div className="text-sm uppercase tracking-wide text-yellow-400 mb-3">
              Strategic Risks
            </div>

            <ul className="space-y-2">
              {briefing.race_engineer_briefing.risks.map((risk, idx) => (
                <li key={idx} className="text-zinc-300">
                  • {risk}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
