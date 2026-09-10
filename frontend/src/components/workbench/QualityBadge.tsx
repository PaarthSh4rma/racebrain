import type { DataQuality } from "../../types/historical";

const tones = {
  good: { tone: "positive", className: "border-emerald-900/70 text-emerald-400/80" },
  degraded: { tone: "caution", className: "border-amber-700 bg-amber-950/30 text-amber-300" },
  insufficient: { tone: "warning", className: "border-red-600 bg-red-950/40 text-red-300" },
  unknown: { tone: "neutral", className: "border-slate-600 text-slate-400" },
} as const;

export default function QualityBadge({ level, quiet = false }: { level: DataQuality["level"]; quiet?: boolean }) {
  const style = tones[level];
  return <span data-quality-tone={style.tone} className={`px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${quiet && level === "good" ? "border-0" : "border"} ${style.className}`}>{level}</span>;
}
