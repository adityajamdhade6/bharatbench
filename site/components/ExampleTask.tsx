import { formatAnswer } from "@/lib/format";
import type { Example } from "@/lib/types";

export function ExampleTask({ ex, languageLabels }: { ex: Example; languageLabels: Record<string, string> }) {
  const long = ex.prompt.length > 450;
  return (
    <article className="rounded-xl border border-line bg-surface p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-muted">
        <span className="font-mono text-fg">{ex.id}</span>
        <span className="rounded-full border border-line px-2 py-0.5">{languageLabels[ex.language] ?? ex.language}</span>
        <span className="rounded-full border border-line px-2 py-0.5">{ex.difficulty}</span>
        <span className="rounded-full border border-line px-2 py-0.5">{ex.answer_type}</span>
      </div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Prompt</h3>
      {long ? (
        <details className="mt-1">
          <summary className="cursor-pointer text-sm">{ex.prompt.slice(0, 160).trim()}… <span className="text-accent">show full prompt</span></summary>
          <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-bg p-3 text-sm">{ex.prompt}</pre>
        </details>
      ) : (
        <pre className="mt-1 whitespace-pre-wrap break-words rounded-lg bg-bg p-3 text-sm">{ex.prompt}</pre>
      )}
      <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted">{ex.answer_type === "rubric" ? "Rubric" : "Reference answer"}</h3>
      <pre className="mt-1 whitespace-pre-wrap break-words rounded-lg bg-bg p-3 text-sm">{formatAnswer(ex.reference_answer)}</pre>
      {ex.worked_solution && (
        <>
          <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted">Worked solution</h3>
          <p className="mt-1 text-sm">{ex.worked_solution}</p>
        </>
      )}
      {ex.source_url && (
        <p className="mt-3 text-sm">
          <span className="text-muted">Source: </span>
          <a href={ex.source_url} className="break-all text-accent underline" rel="noopener noreferrer" target="_blank">{ex.source_url}</a>
        </p>
      )}
    </article>
  );
}
