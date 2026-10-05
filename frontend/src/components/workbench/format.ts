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

export function formatUtcTime(value: string | null | undefined): string {
  if (!value) return missing;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return missing;
  return `${date.toISOString().slice(11, 23)} UTC`;
}

export function formatNumber(value: number | null, suffix = ""): string {
  return value === null ? missing : `${value}${suffix}`;
}

export function formatPace(value: number | null | undefined): string {
  return value === null || value === undefined ? missing : `${value.toFixed(3)} s/lap`;
}

export function formatSlope(value: number | null | undefined): string {
  if (value === null || value === undefined) return missing;
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(3)} s/lap/lap`;
}

export function humanize(value: string | null | undefined): string {
  return value ? value.replaceAll("_", " ") : missing;
}
