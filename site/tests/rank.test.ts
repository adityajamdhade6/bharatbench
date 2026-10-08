import { describe, expect, it } from "vitest";
import { hinglishGap } from "@/lib/gap";
import { intervalsOverlap, ranks, sortModels } from "@/lib/rank";
import type { ModelResult, Stat } from "@/lib/types";

const stat = (mean: number, lo = mean - 0.05, hi = mean + 0.05, n = 20): Stat => ({ n, mean, ci95: [lo, hi] });
const model = (label: string, overall: number | null, cats: Record<string, number> = {}, langs: Record<string, Stat> = {}): ModelResult => ({
  id: `p/${label}`, provider: "p", model: label, label,
  overall: overall === null ? null : stat(overall),
  categories: Object.fromEntries(Object.entries(cats).map(([k, v]) => [k, stat(v)])),
  languages: langs, api_errors_excluded: 0, unscored: 0,
});

const A = model("alpha", 0.7, { gst: 0.9 });
const B = model("bravo", 0.8, { gst: 0.5 });
const C = model("charlie", null);
const D = model("delta", 0.7, {});

describe("sortModels", () => {
  it("sorts by overall, descending", () => {
    expect(sortModels([A, B, D], "overall", "desc").map((m) => m.label)).toEqual(["bravo", "alpha", "delta"]);
  });
  it("breaks ties by name so the order is stable", () => {
    expect(sortModels([D, A], "overall", "desc").map((m) => m.label)).toEqual(["alpha", "delta"]);
  });
  it("sorts by a category and puts missing scores last in both directions", () => {
    expect(sortModels([B, A, D], "gst", "desc").map((m) => m.label)).toEqual(["alpha", "bravo", "delta"]);
    expect(sortModels([B, A, D], "gst", "asc").map((m) => m.label)).toEqual(["bravo", "alpha", "delta"]);
  });
  it("sorts by name and does not mutate its input", () => {
    const input = [B, A];
    expect(sortModels(input, "model", "asc").map((m) => m.label)).toEqual(["alpha", "bravo"]);
    expect(input.map((m) => m.label)).toEqual(["bravo", "alpha"]);
  });
  it("uses raw means, not rounded ones", () => {
    const x = model("x", 0.70001);
    const y = model("y", 0.70002);
    expect(sortModels([x, y], "overall", "desc").map((m) => m.label)).toEqual(["y", "x"]);
  });
});

describe("ranks", () => {
  it("gives equal means the same rank and skips the next", () => {
    const r = ranks([A, B, D], "overall");
    expect([r.get(B.id), r.get(A.id), r.get(D.id)]).toEqual([1, 2, 2]);
  });
  it("gives null to models without a score", () => expect(ranks([A, C], "overall").get(C.id)).toBeNull());
});

describe("intervalsOverlap", () => {
  it("detects overlap and separation", () => {
    expect(intervalsOverlap(stat(0.5, 0.4, 0.6), stat(0.55, 0.45, 0.65))).toBe(true);
    expect(intervalsOverlap(stat(0.3, 0.2, 0.4), stat(0.8, 0.7, 0.9))).toBe(false);
  });
});

describe("hinglishGap", () => {
  const withLangs = (label: string, en: number, hg: number) => model(label, 0.5, {}, { en: stat(en), hinglish: stat(hg) });
  it("computes english minus hinglish and sorts by widest gap", () => {
    const rows = hinglishGap([withLangs("a", 0.8, 0.7), withLangs("b", 0.9, 0.5)]);
    expect(rows.map((r) => r.model.label)).toEqual(["b", "a"]);
    expect(rows[0].gap).toBeCloseTo(0.4);
  });
  it("skips models missing either language", () => {
    expect(hinglishGap([model("z", 0.5, {}, { en: stat(0.8) })])).toEqual([]);
  });
});

import { leaders } from "@/lib/rank";

describe("leaders", () => {
  it("returns the single best model", () => {
    expect(leaders([A, B], "overall").map((m) => m.label)).toEqual(["bravo"]);
  });
  it("returns every model tied on the top raw score, by name", () => {
    expect(leaders([D, A], "overall").map((m) => m.label)).toEqual(["alpha", "delta"]);
  });
  it("ignores models without a score and handles none", () => {
    expect(leaders([C], "overall")).toEqual([]);
    expect(leaders([], "overall")).toEqual([]);
  });
});
