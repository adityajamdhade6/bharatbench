import { describe, expect, it } from "vitest";
import { formatAnswer, formatDate, formatDistinct, pct, ppDiff } from "@/lib/format";

describe("pct", () => {
  it("formats a proportion", () => expect(pct(0.7234)).toBe("72.3%"));
  it("supports decimals", () => expect(pct(0.95, 0)).toBe("95%"));
});

describe("formatDistinct", () => {
  it("uses one decimal when values differ at that precision", () => {
    expect(formatDistinct([0.81, 0.72])).toEqual(["81.0%", "72.0%"]);
  });
  it("adds decimals so different scores never look equal (display must not hide a ranking)", () => {
    const out = formatDistinct([0.7234, 0.7231]);
    expect(out[0]).not.toBe(out[1]);
    expect(out).toEqual(["72.34%", "72.31%"]);
  });
  it("keeps genuinely equal values equal", () => {
    expect(formatDistinct([0.5, 0.5])).toEqual(["50.0%", "50.0%"]);
  });
  it("handles empty input", () => expect(formatDistinct([])).toEqual([]));
});

describe("formatDate", () => {
  it("is UTC based and readable", () => expect(formatDate("2026-10-07T23:59:00+00:00")).toBe("7 Oct 2026"));
  it("returns the input when unparseable", () => expect(formatDate("not a date")).toBe("not a date"));
});

describe("ppDiff", () => {
  it("shows sign and percentage points", () => {
    expect(ppDiff(0.6, 0.8)).toBe("−20.0 pp");
    expect(ppDiff(0.8, 0.6)).toBe("+20.0 pp");
    expect(ppDiff(0.5, 0.5)).toBe("0.0 pp");
  });
});

describe("formatAnswer", () => {
  it("handles strings, rubrics and extraction objects", () => {
    expect(formatAnswer("District")).toBe("District");
    expect(formatAnswer(["a", "b"])).toBe("• a\n• b");
    expect(formatAnswer({ x: 1 })).toBe('{\n  "x": 1\n}');
    expect(formatAnswer(42)).toBe("42");
  });
});
