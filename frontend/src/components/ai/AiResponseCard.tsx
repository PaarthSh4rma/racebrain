import type { AiResponse } from "../../types/ai";

function ListBlock({
  title,
  items,
}: {
  title: string;
  items?: string[];
}) {
  if (!items || items.length === 0) return null;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-sm uppercase tracking-[0.2em] text-white/40">
        {title}
      </p>

      <ul className="mt-3 space-y-2 text-white/70">
        {items.map((item, index) => (
          <li key={index}>• {item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function AiResponseCard({
  response,
}: {
  response: AiResponse;
}) {
  return (
    <div className="mt-6 space-y-4">
      <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">
          Engineer Summary
        </p>
        <p className="mt-3 whitespace-pre-line text-white/80">
          {response.response ?? response.summary}
        </p>
      </div>

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

      <ListBlock title="Analysis" items={response.points} />
      <ListBlock title="Key Factors" items={response.key_factors} />
      <ListBlock title="Tradeoffs" items={response.tradeoffs} />

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
    </div>
  );
}