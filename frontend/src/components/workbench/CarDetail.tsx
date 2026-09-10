import type { CarState } from "../../types/historical";
import { formatGap, formatUtc, missing } from "./format";

export default function CarDetail({ car }: { car: CarState | null }) {
  if (!car) return <aside className="border border-slate-700 bg-slate-950 p-4 text-sm text-slate-400">Select a field entry to inspect its canonical evidence.</aside>;
  const facts = [
    ["Position", car.position], ["Completed lap", car.current_lap], ["Observed", formatUtc(car.observed_at)],
    ["Gap ahead", formatGap(car.gap_ahead)], ["Gap to leader", formatGap(car.gap_to_leader)],
    ["Tyre", car.tyre?.compound.toUpperCase()], ["Tyre age", car.tyre ? `${car.tyre.age_laps} laps` : null], ["Stint", car.tyre?.stint_number],
  ];
  if (car.pit_stop_count !== null) facts.push(["Pit stops", car.pit_stop_count]);
  if (car.in_pit !== null) facts.push(["In pit", car.in_pit ? "Yes" : "No"]);
  return (
    <aside className="border border-slate-700 bg-slate-950 xl:sticky xl:top-4 xl:self-start" aria-labelledby="car-detail-heading">
      <header className="border-b border-slate-700 px-4 py-3"><p className="text-[10px] uppercase tracking-widest text-slate-500">Selected entry</p><h2 id="car-detail-heading" className="text-lg font-semibold">{car.driver_name ?? "Unknown entry"}</h2></header>
      <dl className="grid grid-cols-2 gap-px bg-slate-800">
        {facts.map(([label, value]) => <div key={String(label)} className="bg-slate-950 px-3 py-2"><dt className="text-[10px] uppercase tracking-wider text-slate-500">{label}</dt><dd className="mt-1 font-mono text-sm text-slate-100">{value ?? missing}</dd></div>)}
      </dl>
      <div className="border-t border-slate-800 p-4 text-xs">
        <p className="font-semibold uppercase tracking-wider text-slate-400">Data quality · {car.data_quality.level}</p>
        {car.data_quality.missing_fields.length > 0 && <p className="mt-2 text-amber-200">Missing: {car.data_quality.missing_fields.join(", ")}</p>}
        {car.data_quality.warnings.map((warning) => <p key={warning} className="mt-2 text-slate-300">{warning}</p>)}
      </div>
      <details className="border-t border-slate-800 p-4">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-cyan-300">Provider evidence</summary>
        <div className="mt-3 space-y-3">
          {car.provenance.map((item, index) => <div key={`${item.source}-${index}`} className="border-l border-slate-700 pl-3 text-xs"><div className="flex justify-between gap-2"><strong className="capitalize text-slate-200">{item.source}</strong><span className="font-mono text-slate-400">{formatUtc(item.observed_at)}</span></div>{item.transformations.map((text) => <p key={text} className="mt-1 text-slate-400">{text}</p>)}</div>)}
        </div>
      </details>
    </aside>
  );
}
