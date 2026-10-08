import type { ModelResult, Stat } from "./types";

export type GapRow = {
  model: ModelResult;
  english: Stat;
  hinglish: Stat;
  /** english.mean - hinglish.mean; positive means Hinglish is lower. */
  gap: number;
};

/** One row per model that has scored both English and Hinglish tasks, widest gap first. */
export function hinglishGap(models: ModelResult[]): GapRow[] {
  const rows: GapRow[] = [];
  for (const model of models) {
    const english = model.languages["en"];
    const hinglish = model.languages["hinglish"];
    if (english && hinglish) rows.push({ model, english, hinglish, gap: english.mean - hinglish.mean });
  }
  return rows.sort((a, b) => b.gap - a.gap || a.model.label.localeCompare(b.model.label));
}
