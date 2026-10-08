import { pct } from "@/lib/format";
import type { Stat } from "@/lib/types";

/** Score with its 95% interval: a thin track, the interval as a band, the mean as a dot. */
export function CiBar({ stat, label }: { stat: Stat; label: string }) {
  const [lo, hi] = stat.ci95;
  return (
    <div
      role="img"
      aria-label={`${label}: ${pct(stat.mean)}, 95% interval ${pct(lo)} to ${pct(hi)}`}
      className="relative h-2 w-full min-w-16 rounded-full bg-track"
    >
      <div className="absolute inset-y-0 rounded-full bg-accent/35" style={{ left: `${lo * 100}%`, width: `${Math.max((hi - lo) * 100, 0.5)}%` }} />
      <div className="absolute top-1/2 h-3 w-1 -translate-x-1/2 -translate-y-1/2 rounded-sm bg-accent" style={{ left: `${stat.mean * 100}%` }} />
    </div>
  );
}
