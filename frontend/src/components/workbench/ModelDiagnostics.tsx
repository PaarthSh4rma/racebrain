import type {
  HistoricalAnalysisResponse,
  ModelLapEvidence,
  ModelVersion,
  PaceRobustnessResult,
  TyreSlopeRobustnessResult,
} from "../../types/historical";
import { formatSlope, humanize, missing } from "./format";

function Version({ label, version }: { label: string; version: ModelVersion }) {
  return <div className="border border-slate-800 bg-slate-950 p-3"><p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-1 text-sm text-slate-200">{version.model_name} · v{version.version}</p><p className="mt-2 break-all font-mono text-[11px] text-slate-500">{version.config_hash}</p></div>;
}

function Laps({ evidence }: { evidence: ModelLapEvidence }) {
  return <div className="grid gap-3 lg:grid-cols-3">
    <div><p className="text-[10px] uppercase tracking-wider text-slate-500">Candidate laps</p><p className="mt-1 font-mono text-xs text-slate-200">{evidence.candidate_laps.join(", ") || missing}</p></div>
    <div><p className="text-[10px] uppercase tracking-wider text-slate-500">Included laps</p><p className="mt-1 font-mono text-xs text-cyan-200">{evidence.included_laps.join(", ") || missing}</p></div>
    <div><p className="text-[10px] uppercase tracking-wider text-slate-500">Excluded laps</p>{evidence.excluded_laps.length ? <ul className="mt-1 space-y-1 font-mono text-xs text-amber-200">{evidence.excluded_laps.map((item) => <li key={item.lap_number}>L{item.lap_number}: {item.reasons.map(humanize).join(", ")}</li>)}</ul> : <p className="mt-1 font-mono text-xs text-slate-400">None</p>}</div>
  </div>;
}

const countSummary = (items: { lap_count: number }[]) => items.reduce((total, item) => total + item.lap_count, 0);

export default function ModelDiagnostics({ result, pace, tyre, evidence }: {
  result: HistoricalAnalysisResponse;
  pace: PaceRobustnessResult | null;
  tyre: TyreSlopeRobustnessResult | null;
  evidence: HistoricalAnalysisResponse["evidence"][number] | null;
}) {
  if (!pace || !tyre || !evidence) return null;
  const paceFit = pace.point_fit;
  const tyreFit = tyre.point_fit;
  return (
    <section className="border border-slate-700 bg-slate-900" aria-labelledby="diagnostics-heading" data-testid="model-diagnostics">
      <header className="border-b border-slate-700 px-4 py-3"><h2 id="diagnostics-heading" className="text-sm font-semibold uppercase tracking-[0.16em]">Model evidence & diagnostics</h2><p className="mt-1 text-xs text-slate-500">Exact accepted evidence, exclusions, fit diagnostics, limitations, and immutable model identity.</p></header>
      <details className="group border-b border-slate-800 p-4">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-cyan-300">Pace evidence & diagnostics</summary>
        <div className="mt-4 space-y-5">
          <Laps evidence={evidence.pace} />
          <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div><dt className="text-[10px] uppercase text-slate-500">Candidate / included / excluded</dt><dd className="mt-1 font-mono text-sm">{paceFit.diagnostics.candidate_laps} / {paceFit.diagnostics.included_laps} / {paceFit.diagnostics.excluded_laps}</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Evidence window</dt><dd className="mt-1 font-mono text-sm">{paceFit.estimate ? `L${paceFit.estimate.evidence_window.first_lap}–L${paceFit.estimate.evidence_window.last_lap}` : missing}</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Residual median</dt><dd className="mt-1 font-mono text-sm">{paceFit.diagnostics.residual_median_s?.toFixed(3) ?? missing} s</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Residual MAD</dt><dd className="mt-1 font-mono text-sm">{paceFit.diagnostics.residual_median_absolute_s?.toFixed(3) ?? missing} s</dd></div>
          </dl>
          <p className="text-xs text-slate-400">Recorded exclusions: {countSummary(paceFit.selection_audit.hard_exclusions)} factual · {countSummary(paceFit.selection_audit.warning_exclusions)} configured warning.</p>
          <div className="grid gap-3 md:grid-cols-2"><Version label="Point model" version={pace.point_model_version} /><Version label="Robustness model" version={pace.robustness_model_version} /></div>
          <ul className="list-disc space-y-1 pl-5 text-xs text-slate-400">{pace.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      </details>
      <details className="group border-b border-slate-800 p-4">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-cyan-300">Tyre evidence & diagnostics</summary>
        <div className="mt-4 space-y-5">
          <Laps evidence={evidence.tyre_age_slope} />
          <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div><dt className="text-[10px] uppercase text-slate-500">Stint / compound</dt><dd className="mt-1 font-mono text-sm">{tyreFit.diagnostics.stint_number ?? missing} / {tyreFit.diagnostics.compound?.toUpperCase() ?? missing}</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Tyre-age span</dt><dd className="mt-1 font-mono text-sm">{tyreFit.diagnostics.minimum_tyre_age_laps ?? missing}–{tyreFit.diagnostics.maximum_tyre_age_laps ?? missing} ({tyreFit.diagnostics.tyre_age_span_laps ?? missing})</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Intercept</dt><dd className="mt-1 font-mono text-sm">{tyreFit.diagnostics.intercept_s?.toFixed(3) ?? missing} s</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Residual median / MAD</dt><dd className="mt-1 font-mono text-sm">{tyreFit.diagnostics.residual_median_s?.toFixed(3) ?? missing} / {tyreFit.diagnostics.residual_median_absolute_s?.toFixed(3) ?? missing} s</dd></div>
          </dl>
          {tyre.diagnostics ? <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div><dt className="text-[10px] uppercase text-slate-500">Nominal slope</dt><dd className="mt-1 font-mono text-sm">{formatSlope(tyre.diagnostics.nominal_slope_s_per_lap_per_lap)}</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">LOO refits</dt><dd className="mt-1 font-mono text-sm">{tyre.diagnostics.leave_one_out_refit_count}</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">LOO min / max</dt><dd className="mt-1 font-mono text-sm">{tyre.diagnostics.leave_one_out_min_s_per_lap_per_lap.toFixed(3)} / {tyre.diagnostics.leave_one_out_max_s_per_lap_per_lap.toFixed(3)}</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Sign counts N / 0 / P</dt><dd className="mt-1 font-mono text-sm">{tyre.diagnostics.sign_counts.negative} / {tyre.diagnostics.sign_counts.zero} / {tyre.diagnostics.sign_counts.positive}</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Sensitivity envelope</dt><dd className="mt-1 font-mono text-sm">{formatSlope(tyre.diagnostics.sensitivity_envelope.lower)} → {formatSlope(tyre.diagnostics.sensitivity_envelope.upper)}</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Maximum deviation</dt><dd className="mt-1 font-mono text-sm">{tyre.diagnostics.maximum_absolute_deviation_s_per_lap_per_lap.toFixed(4)}</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Influential omission</dt><dd className="mt-1 font-mono text-sm">Lap {tyre.diagnostics.most_influential_omitted_lap}</dd></div>
            <div><dt className="text-[10px] uppercase text-slate-500">Sign stability</dt><dd className="mt-1 text-sm font-semibold">{tyre.diagnostics.sign_stable ? "SIGN STABLE" : "SIGN UNSTABLE"}</dd></div>
          </dl> : <p className="border-l-2 border-amber-500 pl-3 text-sm text-amber-200">Robustness unavailable: {humanize(tyre.unavailable_reason)}</p>}
          <div className="grid gap-3 md:grid-cols-2"><Version label="Point model" version={tyre.point_model_version} /><Version label="Robustness model" version={tyre.robustness_model_version} /></div>
          <ul className="list-disc space-y-1 pl-5 text-xs text-slate-400">{tyre.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      </details>
      <details className="p-4">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-cyan-300">Context build diagnostics</summary>
        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4 lg:grid-cols-6">
          {[['Source lap rows', result.modelling_diagnostics.source_lap_rows], ['Admitted', result.modelling_diagnostics.admitted_observations], ['Bounded out', result.modelling_diagnostics.rows_bounded_out], ['Conflicts', result.modelling_diagnostics.conflicting_laps], ['Tyre annotations', result.modelling_diagnostics.tyre_annotations], ['Pit affected', result.modelling_diagnostics.pit_lane_affected_observations]].map(([label, value]) => <div key={String(label)}><dt className="text-[10px] uppercase tracking-wider text-slate-500">{label}</dt><dd className="mt-1 font-mono text-slate-200">{value}</dd></div>)}
        </dl>
      </details>
    </section>
  );
}
