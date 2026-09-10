import type { CarState } from "../../types/historical";
import { formatGap, missing } from "./format";

export default function FieldTable({ cars, selectedId, onSelect }: { cars: CarState[]; selectedId?: string; onSelect: (car: CarState) => void }) {
  const sorted = [...cars].sort((a, b) => (a.position ?? 999) - (b.position ?? 999) || (a.driver_name ?? "").localeCompare(b.driver_name ?? ""));
  return (
    <section className="overflow-hidden border border-slate-700 bg-slate-950" aria-labelledby="field-heading">
      <div className="flex items-center justify-between border-b border-slate-700 px-4 py-3">
        <h2 id="field-heading" className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-200">Full field</h2>
        <span className="text-xs text-slate-400">{cars.length} reconstructed entries</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] border-collapse text-left text-sm">
          <thead className="bg-slate-900 text-[11px] uppercase tracking-wider text-slate-400">
            <tr>{["Pos", "Driver", "Completed lap", "Gap ahead", "Gap to leader", "Tyre", "Age", "Quality"].map((label) => <th key={label} className="px-3 py-2 font-medium">{label}</th>)}</tr>
          </thead>
          <tbody>
            {sorted.map((car) => (
              <tr key={car.competitor_id} data-quality={car.data_quality.level} className={`cursor-pointer border-t border-slate-800 hover:bg-slate-800/70 ${selectedId === car.competitor_id ? "bg-cyan-950/60" : car.data_quality.level !== "good" ? "bg-amber-950/10" : ""}`} onClick={() => onSelect(car)}>
                <td className="px-3 py-2 font-mono text-slate-200">{car.position ?? missing}</td>
                <td className="px-3 py-2 font-medium text-white"><button className="text-left" onClick={() => onSelect(car)}>{car.driver_name ?? "Unknown entry"}</button></td>
                <td className="px-3 py-2 font-mono">{car.current_lap ?? missing}</td>
                <td className="px-3 py-2 font-mono">{formatGap(car.gap_ahead)}</td>
                <td className="px-3 py-2 font-mono">{formatGap(car.gap_to_leader)}</td>
                <td className="px-3 py-2 uppercase">{car.tyre?.compound ?? missing}</td>
                <td className="px-3 py-2 font-mono">{car.tyre?.age_laps ?? missing}</td>
                <td className="px-3 py-2"><span className={`border px-2 py-1 text-[10px] font-bold uppercase ${car.data_quality.level === "good" ? "border-emerald-700 text-emerald-300" : "border-amber-700 text-amber-300"}`}>{car.data_quality.level}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
