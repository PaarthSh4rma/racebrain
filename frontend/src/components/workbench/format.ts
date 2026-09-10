import type { Gap } from "../../types/historical";

export const missing = "—";

export function formatGap(gap: Gap | null): string {
  if (!gap) return missing;
  if (gap.laps !== null) return `+${gap.laps} ${gap.laps === 1 ? "LAP" : "LAPS"}`;
  if (gap.seconds !== null) return `${gap.seconds.toFixed(3).replace(/\.0+$/, ".0")}s`;
  return missing;
}

export function formatUtc(value: string | null | undefined): string {
  if (!value) return missing;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? missing : `${date.toISOString().replace("T", " ").replace(".000Z", "Z")} UTC`;
}

export function formatNumber(value: number | null, suffix = ""): string {
  return value === null ? missing : `${value}${suffix}`;
}
