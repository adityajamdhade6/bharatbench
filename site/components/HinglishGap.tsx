import { pct, ppDiff } from "@/lib/format";
import { hinglishGap } from "@/lib/gap";
import type { ModelResult, Stat } from "@/lib/types";

function Bar({ stat, color, label }: { stat: Stat; color: "accent" | "warm"; label: string }) {
  const [lo, hi] = stat.ci95;
  const bg = color === "accent" ? "bg-accent" : "bg-warm";
  return (
    <div className="flex items-center gap-2" role="img" aria-label={`${label}: ${pct(stat.mean)}, 95% interval ${pct(lo)} to ${pct(hi)}, ${stat.n} tasks`}>
      <div className="relative h-4 flex-1 rounded bg-track">
        <div className={`absolute inset-y-0 left-0 rounded ${bg}`} style={{ width: `${stat.mean * 100}%` }} />
        <div className="absolute top-1/2 h-px -translate-y-1/2 bg-fg" style={{ left: `${lo * 100}%`, width: `${(hi - lo) * 100}%` }} />
        <div className="absolute top-1/2 h-2.5 w-px -translate-y-1/2 bg-fg" style={{ left: `${lo * 100}%` }} />
        <div className="absolute top-1/2 h-2.5 w-px -translate-y-1/2 bg-fg" style={{ left: `${hi * 100}%` }} />
      </div>
      <div className="tabular w-28 shrink-0 text-xs">
        <span className="font-medium">{pct(stat.mean)}</span> <span className="text-muted">n={stat.n}</span>
      </div>
    </div>
  );
}

export function HinglishGap({ models, labels }: { models: ModelResult[]; labels: Record<string, string> }) {
  const rows = hinglishGap(models);
  if (rows.length === 0) return <p className="text-sm text-muted">No model has scored both English and Hinglish tasks yet.</p>;
  const en = labels["en"] ?? "English";
  const hg = labels["hinglish"] ?? "Hinglish";
  return (
    <div>
      <ul className="mb-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted" aria-label="Legend">
        <li className="flex items-center gap-1.5"><span className="inline-block h-3 w-3 rounded-sm bg-accent" />{en}</li>
        <li className="flex items-center gap-1.5"><span className="inline-block h-3 w-3 rounded-sm bg-warm" />{hg}</li>
        <li className="flex items-center gap-1.5"><span className="inline-block h-px w-4 bg-fg" />95% interval</li>
      </ul>
      <ul className="space-y-5">
        {rows.map((r) => (
          <li key={r.model.id}>
            <div className="mb-1.5 flex items-baseline justify-between gap-3">
              <span className="text-sm font-medium">{r.model.label}</span>
              <span className="tabular text-xs text-muted">{hg} vs {en}: {ppDiff(r.hinglish.mean, r.english.mean)}</span>
            </div>
            <div className="space-y-1">
              <Bar stat={r.english} color="accent" label={`${r.model.label}, ${en}`} />
              <Bar stat={r.hinglish} color="warm" label={`${r.model.label}, ${hg}`} />
            </div>
          </li>
        ))}
      </ul>
      <div className="tabular mt-2 flex pr-[7.5rem] text-[10px] text-muted" aria-hidden="true">
        <span className="flex-1">0%</span><span className="flex-1 text-center">50%</span><span className="flex-1 text-right">100%</span>
      </div>
    </div>
  );
}
