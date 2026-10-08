import type { Metadata } from "next";
import { data } from "@/lib/data";
import { formatDate, pct } from "@/lib/format";

export const metadata: Metadata = {
  title: "Methodology",
  description: "How BharatBench tasks were made and verified, how answers are scored, and what the results can and cannot tell you.",
};

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="scroll-mt-6">
      <h2 id={`${id}-h`} className="mb-3 text-xl font-semibold">{title}</h2>
      <div className="space-y-3 text-[15px] leading-relaxed">{children}</div>
    </section>
  );
}

export default function Methodology() {
  const t = data.totals;
  const p = data.params;
  const judge = data.judge;
  const v = judge?.validation;
  const rubricInDataset = t.dataset_by_answer_type["rubric"] ?? 0;
  const labels = data.language_labels;
  const langCounts = Object.entries(t.scored_by_language).sort((a, b) => b[1] - a[1]);
  const notes = data.run_notes;
  const erroring = data.models.filter((m) => m.api_errors_excluded > 0 || m.unscored > 0);

  return (
    <article className="max-w-3xl space-y-12">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Methodology</h1>
        <p className="mt-2 text-muted">
          What the numbers mean, where they come from, and where they are weak. Results are from run {data.run_id}, last updated {formatDate(data.last_updated)}.
        </p>
      </header>

      <Section id="tasks" title="How tasks were made">
        <p>
          Tasks fall into {data.categories.length} categories: {data.categories.map((c) => c.title).join(", ")}. Each task is a
          prompt with a reference answer, a difficulty level, a language ({Object.values(labels).join(", ")}) and an answer type
          (exact, numeric, extraction or rubric). The dataset holds {t.dataset_tasks} tasks; {t.verified_tasks} are verified and{" "}
          {t.scored_tasks} were scored in this run.
        </p>
        <p>
          Every task carries either a worked solution that can be recomputed by hand or an official source link. Calculation tasks
          state the rates and slabs they use inside the prompt, so they test arithmetic and reasoning rather than memory of rules that
          change. Documents (invoices, rent agreements, bank statements) are synthetic: names, GSTINs and account numbers are made up.
          No real personal data is used.
        </p>
        <p>Scored tasks per category:</p>
        <ul className="tabular list-disc space-y-1 pl-5">
          {data.categories.map((c) => <li key={c.id}>{c.title}: {t.scored_by_category[c.id] ?? 0}</li>)}
        </ul>
      </Section>

      <Section id="verification" title="How tasks were verified">
        <p>{data.verification.statement}</p>
        {data.verification.rows.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-line bg-surface">
            <table className="w-full min-w-[28rem] border-collapse text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-muted">
                  <th scope="col" className="px-3 py-2 font-medium">Tasks</th>
                  <th scope="col" className="px-3 py-2 font-medium">How they were confirmed</th>
                </tr>
              </thead>
              <tbody>
                {data.verification.rows.map((r) => (
                  <tr key={r.tasks} className="border-b border-line align-top last:border-0">
                    <th scope="row" className="whitespace-nowrap px-3 py-2 text-left font-mono text-xs font-normal">{r.tasks}</th>
                    <td className="px-3 py-2">{r.method}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data.verification.held_back && <p><strong>Not verified:</strong> {data.verification.held_back}</p>}
      </Section>

      <Section id="scoring" title="How answers are scored">
        <p>Every model is called once per task at temperature {p.temperature}, with no system prompt. Each reply gets a score between 0 and 1:</p>
        <ul className="list-disc space-y-2 pl-5">
          <li><strong>Exact:</strong> the reply must match the reference after ignoring case, spaces and punctuation. &ldquo;District Commission&rdquo; does not match &ldquo;District&rdquo;.</li>
          <li><strong>Numeric:</strong> the final number in the reply is parsed (₹, commas, lakh and crore are understood) and must be within {pct(p.numeric_relative_tolerance)} of the reference, or the task&rsquo;s own tolerance if that is larger.</li>
          <li><strong>Extraction:</strong> the reply must contain a JSON object; the score is the share of reference fields that match.</li>
          <li><strong>Rubric:</strong> a language model grades the reply 0, 1 or 2 against a written rubric; the score is that grade divided by 2.</li>
        </ul>
        <p>
          A model&rsquo;s score in a category is the average over its scored tasks. Replies that failed because of an API error are
          excluded rather than counted wrong, and the count is kept alongside the results.
        </p>
      </Section>

      <Section id="intervals" title="Confidence intervals">
        <p>
          Intervals are {pct(data.bootstrap.level, 0)} percentile bootstrap intervals: the scored tasks are resampled with replacement{" "}
          {data.bootstrap.iterations.toLocaleString("en-GB")} times and the middle {pct(data.bootstrap.level, 0)} of the resulting
          averages is shown. They capture the luck of which tasks were chosen, not variation between repeated runs. With few tasks per
          category the intervals are wide; when two models&rsquo; intervals overlap, treat their order as unsettled.
        </p>
      </Section>

      <Section id="judge" title="Judge agreement">
        {data.rubric_skipped || !judge ? (
          <p>
            This run does not use the language-model judge: the {rubricInDataset} rubric tasks in the dataset are left out of every
            score. A judge will only be used after its grades have been compared with hand grades and agree on at least{" "}
            {pct(p.judge_agreement_threshold, 0)} of items.
          </p>
        ) : v ? (
          <p>
            Rubric tasks were graded by {judge.model}. On {v.n} hand-graded replies it agreed exactly with the human grade on{" "}
            {pct(v.exact_agreement)} of them (threshold {pct(p.judge_agreement_threshold, 0)}): {v.passed ? "it passed." : "it did not pass, so rubric scores should not be trusted."}
          </p>
        ) : (
          <p>
            Rubric tasks were graded by {judge.model}. That judge has <strong>not</strong> been validated against hand grades, so
            rubric scores are provisional.
          </p>
        )}
        <details>
          <summary className="cursor-pointer text-sm text-accent">Judge scale</summary>
          <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-surface p-3 text-sm">{p.rubric_scale}</pre>
        </details>
      </Section>

      <Section id="limitations" title="Limitations">
        <ul className="list-disc space-y-2 pl-5">
          <li>The tasks were written with AI assistance and checked as described above. Treat this as a careful draft, not an audited exam.</li>
          <li>Each category has a modest number of tasks, so single scores carry real uncertainty; see the intervals.</li>
          <li>
            The language comparison is confounded: Hinglish and Hindi tasks are mostly customer-support and banking questions, while
            English tasks include harder calculations. A gap between languages is not purely a language effect. Scored tasks by language:{" "}
            {langCounts.map(([k, n]) => `${labels[k] ?? k} ${n}`).join(", ")}.
          </li>
          <li>Each model was run once at temperature {p.temperature}. Results can shift with a different prompt wording, a model update or a different serving provider.</li>
          <li>Exact and numeric scoring are strict about format; a correct answer buried in a long explanation can score zero.</li>
          <li>Laws, rates and RBI rules change. Tasks reflect the sources they cite as of {formatDate(data.last_updated)}.</li>
          {(notes.note || notes.repaired_replies > 0 || notes.excluded_replies > 0) && (
            <li>
              How replies were obtained: {notes.note}{" "}
              {notes.repaired_replies} of {notes.total_replies} replies were retried with a larger output budget because a reasoning
              model had used its whole budget thinking and returned nothing; {notes.excluded_replies} could not be retried and are
              excluded from the scores rather than counted as wrong.
            </li>
          )}
          {erroring.length > 0 && (
            <li>
              Some replies were excluded or unscored:{" "}
              {erroring.map((m) => `${m.label} (${m.api_errors_excluded} API errors, ${m.unscored} unscored)`).join("; ")}.
            </li>
          )}
        </ul>
      </Section>
    </article>
  );
}
