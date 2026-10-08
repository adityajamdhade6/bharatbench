import type { ModelResult, Stat } from "./types";

export type SortKey = "model" | "overall" | string; // string = a category id

export function statFor(m: ModelResult, key: SortKey): Stat | null {
  if (key === "overall") return m.overall;
  return m.categories[key] ?? null;
}

/**
 * Sort by model name, overall, or a category. Missing scores always sort last,
 * whichever direction is chosen. Ties fall back to name so the order is stable.
 * Uses the raw means, never rounded display values.
 */
export function sortModels(models: ModelResult[], key: SortKey, dir: "asc" | "desc"): ModelResult[] {
  const sign = dir === "asc" ? 1 : -1;
  return [...models].sort((a, b) => {
    if (key === "model") return sign * a.label.localeCompare(b.label);
    const sa = statFor(a, key);
    const sb = statFor(b, key);
    if (!sa && !sb) return a.label.localeCompare(b.label);
    if (!sa) return 1;
    if (!sb) return -1;
    return sign * (sa.mean - sb.mean) || a.label.localeCompare(b.label);
  });
}

/** 1-based rank by a score, best first. Models with identical raw means share a rank. */
export function ranks(models: ModelResult[], key: SortKey): Map<string, number | null> {
  const ordered = sortModels(models, key, "desc");
  const out = new Map<string, number | null>();
  let prev: number | null = null;
  let prevRank = 0;
  ordered.forEach((m, i) => {
    const s = statFor(m, key);
    if (!s) return void out.set(m.id, null);
    const rank = prev !== null && s.mean === prev ? prevRank : i + 1;
    out.set(m.id, rank);
    prev = s.mean;
    prevRank = rank;
  });
  return out;
}

/** True when two models' 95% intervals overlap, i.e. their order is not clearly established. */
export function intervalsOverlap(a: Stat, b: Stat): boolean {
  return a.ci95[0] <= b.ci95[1] && b.ci95[0] <= a.ci95[1];
}

/** Every model sharing the top raw score for a key (more than one means a tie). */
export function leaders(models: ModelResult[], key: SortKey): ModelResult[] {
  const scored = models.filter((m) => statFor(m, key));
  if (scored.length === 0) return [];
  const top = Math.max(...scored.map((m) => statFor(m, key)!.mean));
  return scored.filter((m) => statFor(m, key)!.mean === top).sort((a, b) => a.label.localeCompare(b.label));
}
