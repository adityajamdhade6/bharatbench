import Link from "next/link";
import { HinglishGap } from "@/components/HinglishGap";
import { Leaderboard } from "@/components/Leaderboard";
import { data } from "@/lib/data";
import { formatDate, pct } from "@/lib/format";
import { leaders, statFor } from "@/lib/rank";

export default function Home() {
  const t = data.totals;
  return (
    <div className="space-y-14">
      <section>
        <h1 className="max-w-3xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          How well do LLMs handle real Indian tasks?
        </h1>
        <p className="tabular mt-3 text-sm text-muted">
          {t.scored_tasks} verified tasks · {t.models} models · last updated {formatDate(data.last_updated)}
        </p>
      </section>

      <section aria-labelledby="leaderboard">
        <h2 id="leaderboard" className="mb-4 text-xl font-semibold">Leaderboard</h2>
        <Leaderboard models={data.models} categories={data.categories} />
      </section>

      <section aria-labelledby="categories">
        <h2 id="categories" className="mb-4 text-xl font-semibold">Categories</h2>
        <ul className="grid gap-3 sm:grid-cols-2">
          {data.categories.map((c) => {
            const top = leaders(data.models, c.id);
            const s = top[0] ? statFor(top[0], c.id) : null;
            return (
              <li key={c.id}>
                <Link href={`/categories/${c.slug}/`} className="block h-full rounded-xl border border-line bg-surface p-4 hover:border-accent">
                  <div className="font-medium">{c.title}</div>
                  <p className="mt-1 text-sm text-muted">{c.description}</p>
                  <p className="tabular mt-3 text-xs text-muted">
                    {data.totals.scored_by_category[c.id]} tasks
                    {top.length === 1 && s ? <> · best: <span className="text-fg">{top[0].label}</span> {pct(s.mean)}</> : null}
                    {top.length > 1 && s ? <> · {top.length} models tied at {pct(s.mean)}</> : null}
                  </p>
                </Link>
              </li>
            );
          })}
        </ul>
      </section>

      <section id="hinglish-gap" aria-labelledby="gap-title" className="scroll-mt-6">
        <h2 id="gap-title" className="text-xl font-semibold">The Hinglish gap</h2>
        <p className="mb-5 mt-1 max-w-2xl text-sm text-muted">
          Accuracy on English tasks versus Hinglish tasks, per model. The tasks are different questions, not translations
          of each other, so read the gap together with the intervals and the note on the{" "}
          <Link href="/methodology/" className="underline">methodology page</Link>.
        </p>
        <HinglishGap models={data.models} labels={data.language_labels} />
      </section>
    </div>
  );
}
