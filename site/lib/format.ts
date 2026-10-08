/** Formatting helpers. Display rounding must never change an ordering. */

/** 0.7234 -> "72.3%". */
export function pct(x: number, decimals = 1): string {
  return `${(x * 100).toFixed(decimals)}%`;
}

/**
 * Format values (in the order given) with the fewest decimals (1..4) at which
 * every pair of different values stays different. Equal values stay equal.
 */
export function formatDistinct(values: number[]): string[] {
  for (let d = 1; d <= 4; d++) {
    const out = values.map((v) => (v * 100).toFixed(d));
    const clash = values.some((v, i) => values.some((w, j) => i < j && v !== w && out[i] === out[j]));
    if (!clash || d === 4) return out.map((s) => `${s}%`);
  }
  return values.map((v) => pct(v));
}

/** "2026-10-07T10:15:00+00:00" -> "7 Oct 2026" (UTC, so it never shifts by timezone). */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

/** Difference of two proportions in percentage points: 0.62, 0.81 -> "-19.0 pp" (a minus b). */
export function ppDiff(a: number, b: number): string {
  const v = (a - b) * 100;
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sign}${Math.abs(v).toFixed(1)} pp`;
}

export function formatAnswer(ref: unknown): string {
  if (typeof ref === "string") return ref;
  if (Array.isArray(ref)) return ref.map((r) => `• ${r}`).join("\n");
  if (ref !== null && typeof ref === "object") return JSON.stringify(ref, null, 2);
  return String(ref);
}
