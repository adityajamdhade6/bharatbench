import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CiBar } from "@/components/CiBar";
import { ExampleTask } from "@/components/ExampleTask";
import { data } from "@/lib/data";
import { formatDistinct, pct } from "@/lib/format";
import { ranks, sortModels, statFor } from "@/lib/rank";

export const dynamicParams = false;

export function generateStaticParams() {
  return data.categories.map((c) => ({ slug: c.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const c = data.categories.find((x) => x.slug === slug);
  return { title: c?.title ?? "Category", description: c?.description };
}

export default async function CategoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const category = data.categories.find((c) => c.slug === slug);
  if (!category) notFound();

  const ordered = sortModels(data.models, category.id, "desc");
  const rank = ranks(data.models, category.id);
  const withStat = ordered.filter((m) => statFor(m, category.id));
  const text = formatDistinct(withStat.map((m) => statFor(m, category.id)!.mean));
  const examples = data.examples[category.id] ?? [];

  return (
    <div className="space-y-12">
      <section>
        <Link href="/" className="text-sm text-muted underline">← Leaderboard</Link>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">{category.title}</h1>
        <p className="mt-2 max-w-2xl text-muted">{category.description}</p>
        <p className="tabular mt-2 text-sm text-muted">{data.totals.scored_by_category[category.id]} verified tasks scored</p>
      </section>

      <section aria-labelledby="ranking">
        <h2 id="ranking" className="mb-4 text-xl font-semibold">Ranking</h2>
        <div className="overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full min-w-[30rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs text-muted">
                <th scope="col" className="w-10 px-3 py-3 font-medium">#</th>
                <th scope="col" className="px-3 py-3 font-medium">Model</th>
                <th scope="col" className="px-3 py-3 font-medium">Score</th>
                <th scope="col" className="px-3 py-3 font-medium">95% interval</th>
                <th scope="col" className="w-28 px-3 py-3 font-medium"><span className="sr-only">Interval chart</span></th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((m) => {
                const s = statFor(m, category.id);
                const idx = withStat.indexOf(m);
                return (
                  <tr key={m.id} className="border-b border-line last:border-0">
                    <td className="tabular px-3 py-3 text-muted">{rank.get(m.id) ?? "–"}</td>
                    <th scope="row" className="px-3 py-3 text-left font-medium">{m.label}</th>
                    <td className="tabular px-3 py-3 font-semibold">{s ? text[idx] : "–"}</td>
                    <td className="tabular whitespace-nowrap px-3 py-3 text-muted">{s ? `${pct(s.ci95[0])} – ${pct(s.ci95[1])}` : "–"}</td>
                    <td className="px-3 py-3">{s && <CiBar stat={s} label={m.label} />}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="examples">
        <h2 id="examples" className="mb-1 text-xl font-semibold">Example tasks</h2>
        <p className="mb-4 text-sm text-muted">A spread across difficulty levels, with the reference answer used for scoring.</p>
        <div className="space-y-4">
          {examples.map((ex) => <ExampleTask key={ex.id} ex={ex} languageLabels={data.language_labels} />)}
        </div>
      </section>
    </div>
  );
}
