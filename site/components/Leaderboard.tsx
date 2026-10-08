"use client";

import { useMemo, useState } from "react";
import { formatDistinct, pct } from "@/lib/format";
import { ranks, sortModels, statFor, type SortKey } from "@/lib/rank";
import type { Category, ModelResult } from "@/lib/types";
import { CiBar } from "./CiBar";

type Dir = "asc" | "desc";

export function Leaderboard({ models, categories }: { models: ModelResult[]; categories: Category[] }) {
  const [sort, setSort] = useState<{ key: SortKey; dir: Dir }>({ key: "overall", dir: "desc" });
  const sorted = useMemo(() => sortModels(models, sort.key, sort.dir), [models, sort]);
  const overallRank = useMemo(() => ranks(models, "overall"), [models]);

  // Display strings: fewest decimals at which different scores in a column still look different.
  const shown = useMemo(() => {
    const out: Record<string, Map<string, string>> = {};
    for (const key of ["overall", ...categories.map((c) => c.id)]) {
      const withStat = models.filter((m) => statFor(m, key));
      const text = formatDistinct(withStat.map((m) => statFor(m, key)!.mean));
      out[key] = new Map(withStat.map((m, i) => [m.id, text[i]]));
    }
    return out;
  }, [models, categories]);

  const columns: { key: SortKey; label: string }[] = [
    { key: "overall", label: "Overall" },
    ...categories.map((c) => ({ key: c.id, label: c.title })),
  ];

  function toggle(key: SortKey) {
    setSort((s) => (s.key === key ? { key, dir: s.dir === "desc" ? "asc" : "desc" } : { key, dir: key === "model" ? "asc" : "desc" }));
  }
  const ariaSort = (key: SortKey) => (sort.key === key ? (sort.dir === "asc" ? "ascending" : "descending") : "none");
  const arrow = (key: SortKey) => (sort.key === key ? (sort.dir === "asc" ? " ↑" : " ↓") : "");

  return (
    <div>
      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[44rem] border-collapse text-sm">
          <caption className="sr-only">Model scores by category. Click a column heading to sort.</caption>
          <thead>
            <tr className="border-b border-line text-left text-xs text-muted">
              <th scope="col" className="w-10 px-3 py-3 font-medium">#</th>
              <th scope="col" aria-sort={ariaSort("model")} className="bg-surface px-3 py-3 font-medium sm:sticky sm:left-0 sm:z-10">
                <button onClick={() => toggle("model")} className="font-medium hover:text-fg">Model{arrow("model")}</button>
              </th>
              {columns.map((c) => (
                <th key={c.key} scope="col" aria-sort={ariaSort(c.key)} className="px-3 py-3 font-medium">
                  <button onClick={() => toggle(c.key)} className="text-left font-medium hover:text-fg">{c.label}{arrow(c.key)}</button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((m) => (
              <tr key={m.id} className="border-b border-line last:border-0">
                <td className="tabular px-3 py-3 text-muted">{overallRank.get(m.id) ?? "–"}</td>
                <th scope="row" className="min-w-32 bg-surface px-3 py-3 text-left font-medium sm:sticky sm:left-0 sm:z-10">
                  <div>{m.label}</div>
                  <div className="text-xs font-normal text-muted">{m.provider}</div>
                </th>
                {columns.map((c) => {
                  const s = statFor(m, c.key);
                  return (
                    <td key={c.key} className="tabular px-3 py-3 align-top">
                      {s ? (
                        <>
                          <div className={c.key === "overall" ? "font-semibold" : ""}>{shown[c.key].get(m.id)}</div>
                          <div className="whitespace-nowrap text-xs text-muted">{pct(s.ci95[0])}–{pct(s.ci95[1])}</div>
                          {c.key === "overall" && <div className="mt-1.5 w-24"><CiBar stat={s} label={m.label} /></div>}
                        </>
                      ) : (
                        <span className="text-muted">–</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-muted">
        Small print under each score is the 95% confidence interval. When two models&rsquo; intervals overlap, their order is not
        clearly established. Rank is by overall score.
      </p>
    </div>
  );
}
