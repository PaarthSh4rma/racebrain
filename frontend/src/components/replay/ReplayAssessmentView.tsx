import type { ReplayAssessment } from "../../types/raceData";

function Metric({
  label,
  value,
  testId,
}: {
  label: string;
  value: string;
  testId?: string;
}) {
  return (
    <div className="min-w-0 rounded-xl border border-white/10 bg-black/30 p-3">
      <p className="break-words text-xs uppercase tracking-[0.15em] text-white/40">
        {label}
      </p>
      <p
        className="mt-1 break-words text-lg font-black text-white"
        data-testid={testId}
      >
        {value}
      </p>
    </div>
  );
}

export default function ReplayAssessmentView({
  assessment,
}: {
  assessment: ReplayAssessment;
}) {
  const { snapshot, recommendation, alternatives, recommended_alternative } =
    assessment;
  const maxDelta = Math.max(
    1,
    ...alternatives.map((item) => item.delta_to_recommended),
  );

  return (
    <div className="space-y-4" data-testid="replay-result">
      <p className="break-words text-sm text-white/60">
        {snapshot.session.year} {snapshot.session.country_name} ·{" "}
        {snapshot.session.session_name} ·{" "}
        {snapshot.driver.full_name ?? snapshot.driver.name_acronym ?? `Driver ${snapshot.driver.driver_number}`}
        {" "}· latest fully completed lap {snapshot.decision_lap}
        {snapshot.cutoff_timestamp
          ? ` · cutoff ${new Date(snapshot.cutoff_timestamp).toLocaleString()}`
          : " · lap-number-only cutoff"}
      </p>
      <article className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4 sm:p-5">
        <p className="text-xs uppercase tracking-[0.2em] text-cyan-400">
          Strategy at This Moment
        </p>
        <h3 className="mt-2 break-words text-2xl font-black capitalize sm:text-3xl">
          {recommendation.recommendation.replaceAll("_", " ")}
        </h3>
        <p className="mt-3 text-white/75">{recommendation.summary}</p>
        <div className="mt-4 flex flex-wrap gap-2 text-sm">
          <span className="rounded-full bg-white/10 px-3 py-1">
            Confidence: {recommendation.confidence}
          </span>
          <span className="rounded-full bg-white/10 px-3 py-1">
            Tyre risk: {recommendation.tyre_risk}
          </span>
        </div>
      </article>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric
          label="Decision Lap"
          value={String(snapshot.decision_lap)}
          testId="decision-lap-value"
        />
        <Metric label="Compound" value={snapshot.current_compound ?? "Unknown"} />
        <Metric
          label="Tyre Age"
          value={
            snapshot.estimated_tyre_age === null
              ? "Unknown"
              : `${snapshot.estimated_tyre_age} laps`
          }
        />
        <Metric
          label="Pace Trend"
          value={snapshot.pace.trend.replaceAll("_", " ")}
        />
      </div>

      <article className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-white/50">
          Recent lap-time trend
        </h3>
        <div
          className="mt-4 flex h-28 items-end gap-2"
          role="img"
          aria-label={`Recent lap times: ${snapshot.pace.recent_lap_times.join(", ")} seconds`}
        >
          {snapshot.pace.recent_lap_times.map((lapTime, index) => {
            const minimum = Math.min(...snapshot.pace.recent_lap_times);
            const height = 40 + Math.min(60, (lapTime - minimum) * 18);
            return (
              <div key={`${index}-${lapTime}`} className="flex min-w-0 flex-1 flex-col items-center">
                <div
                  className="w-full rounded-t bg-cyan-400/70"
                  style={{ height: `${height}%` }}
                />
                <span className="mt-1 text-[10px] text-white/40">{lapTime.toFixed(1)}</span>
              </div>
            );
          })}
        </div>
      </article>

      <article className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-white/50">
          Reconstructed Race State
        </h3>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Metric
            label="Weather"
            value={
              snapshot.weather.rainfall_detected
                ? "Rain detected"
                : snapshot.weather.trend === "unknown"
                  ? "Unavailable"
                  : "Dry"
            }
          />
          <Metric
            label="Race Control"
            value={
              snapshot.race_control.red_flag_active
                ? "Red flag"
                : snapshot.race_control.safety_car_active
                  ? "Safety car"
                  : "No active interruption"
            }
          />
        </div>
        <ul className="mt-4 space-y-2 text-sm text-white/70">
          {recommendation.reasoning_factors.map((factor) => (
            <li key={factor}>• {factor}</li>
          ))}
        </ul>
      </article>

      <article className="rounded-2xl border border-red-500/20 bg-red-500/5 p-4">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-red-300">
          Compared Alternative Calls
        </h3>
        <p className="mt-2 text-sm text-white/50">
          Lower transparent strategy score is preferred. This is not race-win probability.
        </p>
        <div className="mt-4 space-y-3">
          {alternatives.map((alternative) => (
            <div
              key={alternative.alternative}
              className="min-w-0 rounded-xl border border-white/10 bg-black/30 p-3"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <p className="font-black capitalize">
                  {alternative.alternative.replaceAll("_", " ")}
                  {alternative.alternative === recommended_alternative && (
                    <span className="ml-2 text-xs text-red-300">Preferred</span>
                  )}
                </p>
                <p className="text-sm text-white/60">
                  +{alternative.delta_to_recommended.toFixed(2)} score · ±
                  {alternative.uncertainty.toFixed(2)}
                </p>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-red-500"
                  style={{
                    width: `${Math.max(8, 100 - (alternative.delta_to_recommended / maxDelta) * 82)}%`,
                  }}
                />
              </div>
              <p className="mt-2 text-sm text-white/50">{alternative.explanation}</p>
            </div>
          ))}
        </div>
      </article>

      {snapshot.data_quality.warnings.length > 0 && (
        <article
          className="rounded-2xl border border-yellow-500/25 bg-yellow-500/5 p-4 text-yellow-100"
          role="status"
        >
          <h3 className="font-black">Data completeness warning</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {snapshot.data_quality.warnings.map((warning) => (
              <li key={warning}>• {warning}</li>
            ))}
          </ul>
        </article>
      )}
    </div>
  );
}
