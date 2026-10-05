import type { ReactNode } from "react";
import type { CarState, PaceRobustnessResult, TyreSlopeRobustnessResult } from "../../types/historical";
import { formatPace, formatSlope, humanize, missing } from "./format";
import QualityBadge from "./QualityBadge";

const unavailableCopy: Record<string, string> = {
  insufficient_recent_clean_laps: "Insufficient clean laps in the recent lap-number window",
  no_observations: "No admitted modelling observations",
  missing_tyre_annotation: "Latest admitted lap lacks complete tyre evidence",
  unknown_compound: "Latest stint compound is not identified",
  mixed_compound: "Latest stint contains conflicting compound evidence",
  inconsistent_tyre_age_progression: "Latest stint has inconsistent tyre-age progression",
  insufficient_clean_laps: "Insufficient clean laps in latest stint",
  insufficient_tyre_age_span: "Insufficient tyre-age span in latest stint",
  invalid_diagnostic_refit: "Leave-one-out refit is not identifiable",
};

const reason = (value: string | null) => unavailableCopy[value ?? ""] ?? humanize(value);

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return <div><dt className="text-[10px] uppercase tracking-[0.16em] text-slate-500">{label}</dt><dd className="mt-1 font-mono text-sm text-slate-100">{children}</dd></div>;
}

export default function ModelSummary({ car, pace, tyre }: {
  car: CarState | null;
  pace: PaceRobustnessResult | null;
  tyre: TyreSlopeRobustnessResult | null;
}) {
  if (!car || !pace || !tyre) {
    return <section className="border border-slate-700 bg-slate-900 p-5 text-sm text-slate-400">Select a modelled field entry to inspect its analysis.</section>;
  }
  const paceEstimate = pace.point_fit.estimate;
  const quantiles = pace.diagnostics?.quantiles;
  const tyreEstimate = tyre.point_fit.estimate;
  const tyreDiagnostic = tyre.diagnostics;
  const tyreFit = tyre.point_fit.diagnostics;

  return (
    <section className="border border-slate-700 bg-slate-900" aria-labelledby="model-summary-heading" data-testid="model-summary">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-slate-700 px-4 py-3">
        <div><p className="text-[10px] uppercase tracking-[0.22em] text-cyan-400">Selected car model summary</p><h2 id="model-summary-heading" className="mt-1 text-xl font-semibold">{car.driver_name ?? "Unknown entry"}</h2></div>
        <div className="text-right"><p className="text-[10px] uppercase tracking-wider text-slate-500">Race position</p><p className="font-mono text-lg text-slate-100">{car.position ?? missing}</p></div>
      </header>
      <div className="grid gap-px bg-slate-700 xl:grid-cols-2">
        <article className="bg-slate-950 p-4" aria-label="Representative pace analysis">
          <div className="flex items-center justify-between gap-3"><h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">Representative pace</h3><QualityBadge level={pace.data_quality.level} /></div>
          {paceEstimate && quantiles ? <>
            <p className="mt-3 font-mono text-3xl font-semibold tracking-tight text-cyan-300">{formatPace(paceEstimate.value)}</p>
            <div className="mt-4 border-l-2 border-cyan-700 pl-3"><p className="text-[10px] uppercase tracking-wider text-slate-500">Empirical included-lap spread</p><p className="mt-1 font-mono text-base text-slate-100">{quantiles.p10.toFixed(3)} – {quantiles.p90.toFixed(3)} s/lap</p><p className="mt-1 text-xs text-slate-500">Observed accepted laps; not a confidence or prediction interval.</p></div>
            <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="p10">{quantiles.p10.toFixed(3)}</Stat><Stat label="p50">{quantiles.p50.toFixed(3)}</Stat><Stat label="p90">{quantiles.p90.toFixed(3)}</Stat><Stat label="Samples">{paceEstimate.sample_count}</Stat>
            </dl>
          </> : <div className="mt-4 border-l-2 border-amber-500 bg-amber-950/20 p-3"><p className="text-xl font-semibold text-amber-200">Unavailable</p><p className="mt-2 text-sm text-slate-200">{reason(pace.point_fit.unavailable_reason)}</p><p className="mt-2 text-xs text-slate-400">{pace.point_fit.diagnostics.included_laps} clean laps accepted from {pace.point_fit.diagnostics.candidate_laps} candidates.</p></div>}
        </article>

        <article className="bg-slate-950 p-4" aria-label="Tyre-age pace slope analysis">
          <div className="flex items-center justify-between gap-3"><h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">Tyre-age pace slope</h3><QualityBadge level={tyre.data_quality.level} /></div>
          {tyreEstimate ? <>
            <p className="mt-3 font-mono text-3xl font-semibold tracking-tight text-cyan-300">{formatSlope(tyreEstimate.value)}</p>
            <p className="mt-2 text-xs text-slate-500">Observed within-stint association; no fuel, track-evolution, or traffic correction.</p>
            <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Compound">{tyreEstimate.compound.toUpperCase()}</Stat><Stat label="Stint">{tyreEstimate.stint_number}</Stat>
              <Stat label="Age evidence">{tyreEstimate.minimum_tyre_age_laps}–{tyreEstimate.maximum_tyre_age_laps} laps</Stat><Stat label="Samples">{tyreEstimate.sample_count}</Stat>
            </dl>
            {tyreDiagnostic ? <div className="mt-5 grid gap-3 border-t border-slate-800 pt-4 sm:grid-cols-3">
              <Stat label="Sign">{tyreDiagnostic.nominal_sign.toUpperCase()}</Stat>
              <div><dt className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Sign stability</dt><dd className="mt-1 text-sm font-semibold text-slate-100">{tyreDiagnostic.sign_stable ? "SIGN STABLE" : "SIGN UNSTABLE"}</dd><p className="mt-1 text-xs text-slate-500">{tyreDiagnostic.sign_stable ? "All leave-one-out refits retained the nominal slope sign." : "At least one leave-one-out refit changed the nominal slope sign."}</p></div>
              <Stat label="LOO sensitivity">{tyreDiagnostic.sensitivity_envelope.lower > 0 ? "+" : ""}{tyreDiagnostic.sensitivity_envelope.lower.toFixed(3)} → {tyreDiagnostic.sensitivity_envelope.upper > 0 ? "+" : ""}{tyreDiagnostic.sensitivity_envelope.upper.toFixed(3)} s/lap/lap</Stat>
              <Stat label="Influential omission">Lap {tyreDiagnostic.most_influential_omitted_lap}</Stat>
            </div> : <p className="mt-4 border-l-2 border-amber-500 pl-3 text-sm text-amber-200">Robustness unavailable: {reason(tyre.unavailable_reason)}</p>}
          </> : <div className="mt-4 border-l-2 border-amber-500 bg-amber-950/20 p-3"><p className="text-xl font-semibold text-amber-200">Unavailable</p><p className="mt-2 text-sm text-slate-200">Reason: {reason(tyre.point_fit.unavailable_reason)}</p><p className="mt-3 text-xs text-slate-400">Latest stint: {tyreFit.compound?.toUpperCase() ?? "unidentified"}{tyreFit.stint_number ? ` · stint ${tyreFit.stint_number}` : ""} · {tyreFit.included_laps} clean laps.</p><p className="mt-1 text-xs font-medium text-slate-300">No earlier stint substituted.</p></div>}
        </article>
      </div>
    </section>
  );
}
