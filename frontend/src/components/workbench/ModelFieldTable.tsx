import type { CarState, PaceRobustnessResult, TyreSlopeRobustnessResult } from "../../types/historical";
import { formatPace, formatSlope, missing } from "./format";
import QualityBadge from "./QualityBadge";

export default function ModelFieldTable({ cars, pace, tyre, selectedId, onSelect }: {
  cars: CarState[];
  pace: PaceRobustnessResult[];
  tyre: TyreSlopeRobustnessResult[];
  selectedId?: string;
  onSelect: (car: CarState) => void;
}) {
  const paceById = new Map(pace.map((item) => [item.competitor_id, item]));
  const tyreById = new Map(tyre.map((item) => [item.competitor_id, item]));
  const sorted = [...cars].sort((a, b) => (a.position ?? 999) - (b.position ?? 999) || (a.driver_name ?? "").localeCompare(b.driver_name ?? ""));
  return (
    <section className="overflow-hidden border border-slate-700 bg-slate-950" aria-labelledby="model-field-heading" data-testid="model-field-table">
      <div className="flex flex-col gap-2 border-b border-slate-700 px-4 py-3 sm:flex-row sm:items-start sm:justify-between">
        <div><h2 id="model-field-heading" className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-200">Full-field model comparison</h2><p className="mt-1 max-w-3xl text-xs text-slate-500">Observed historical estimates reflect tyre state, fuel load, race phase, traffic, track evolution, and driver management. They are not normalized intrinsic car performance.</p></div>
        <span className="whitespace-nowrap text-xs text-slate-400">{cars.length} canonical entries</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1080px] border-collapse text-left text-sm">
          <thead className="bg-slate-900 text-[10px] uppercase tracking-wider text-slate-400"><tr>{["Pos", "Driver", "Recent pace", "p10–p90", "Pace n", "Tyre", "Age", "Tyre-age slope", "Slope stability", "Pace / tyre quality"].map((label) => <th key={label} className="px-3 py-2 font-medium">{label}</th>)}</tr></thead>
          <tbody>{sorted.map((car) => {
            const paceResult = paceById.get(car.competitor_id);
            const tyreResult = tyreById.get(car.competitor_id);
            const paceEstimate = paceResult?.point_fit.estimate;
            const quantiles = paceResult?.diagnostics?.quantiles;
            const tyreEstimate = tyreResult?.point_fit.estimate;
            return <tr key={car.competitor_id} className={`cursor-pointer border-t border-slate-800 hover:bg-slate-800/70 ${selectedId === car.competitor_id ? "bg-cyan-950/60" : ""}`} onClick={() => onSelect(car)}>
              <td className="px-3 py-2 font-mono">{car.position ?? missing}</td>
              <td className="px-3 py-2"><button className="text-left font-medium text-white" onClick={() => onSelect(car)}>{car.driver_name ?? "Unknown entry"}</button></td>
              <td className="px-3 py-2 font-mono text-cyan-200">{paceEstimate ? formatPace(paceEstimate.value) : "Unavailable"}</td>
              <td className="px-3 py-2 font-mono">{quantiles ? `${quantiles.p10.toFixed(3)}–${quantiles.p90.toFixed(3)}` : missing}</td>
              <td className="px-3 py-2 font-mono">{paceEstimate?.sample_count ?? 0}</td>
              <td className="px-3 py-2 uppercase">{car.tyre?.compound ?? missing}</td>
              <td className="px-3 py-2 font-mono">{car.tyre?.age_laps ?? missing}</td>
              <td className="px-3 py-2 font-mono">{tyreEstimate ? formatSlope(tyreEstimate.value) : "Unavailable"}</td>
              <td className="px-3 py-2 text-xs font-semibold">{tyreResult?.diagnostics ? (tyreResult.diagnostics.sign_stable ? "STABLE" : "UNSTABLE") : missing}</td>
              <td className="px-3 py-2"><div className="flex items-center gap-1">{paceResult ? <QualityBadge level={paceResult.data_quality.level} quiet /> : missing}<span className="text-slate-600">/</span>{tyreResult ? <QualityBadge level={tyreResult.data_quality.level} quiet /> : missing}</div></td>
            </tr>;
          })}</tbody>
        </table>
      </div>
    </section>
  );
}
