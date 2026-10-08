"""Command line.

  bharatbench run --models ... --categories ... --limit N
  bharatbench score --run-id R [--judge MODEL | --skip-rubric]
  bharatbench judge-sample --run-ids R1,R2 --n 50
  bharatbench judge-agree --grades FILE.csv --judge MODEL
  bharatbench export --run-id R --out site/data/leaderboard.json
  bharatbench report --run-id R --out analysis.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .adapters import AdapterError, Settings, build_adapter
from .cache import ResponseCache
from .export import write_export
from .report import compute_facts, update_readme, write_analysis, write_launch
from .runner import TEMPERATURE, run
from .scoring.calibration import read_grades, run_agreement, sample_items, write_sheet
from .scoring.rubric import Judge
from .scoring.run import load_task_map, score_run
from .tasks import load_tasks, resolve_categories
from .validate import validate_dir


def _csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _dirs(p: argparse.ArgumentParser) -> None:
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--results-dir", type=Path, default=Path("results"))
    p.add_argument("--cache-dir", type=Path, default=Path(".cache/responses"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bharatbench")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="run models over the verified tasks")
    r.add_argument("--models", type=_csv, required=True,
                   help="comma-separated aliases (e.g. gemini-flash,llama-3.3-70b) or provider:model-id")
    r.add_argument("--categories", type=_csv, default=None,
                   help="comma-separated: gst, hinglish, docs, law, payments (default: all)")
    r.add_argument("--limit", type=int, default=None, help="max verified tasks PER CATEGORY")
    r.add_argument("--run-id", default=None)
    _dirs(r)

    s = sub.add_parser("score", help="score a finished run -> results/<run_id>/scores.json")
    s.add_argument("--run-id", required=True)
    s.add_argument("--judge", default=None, help="judge model for rubric tasks (use a different model family)")
    s.add_argument("--skip-rubric", action="store_true", help="leave rubric tasks unscored")
    s.add_argument("--judge-agreement", type=Path, default=None,
                   help="agreement JSON from judge-agree, recorded in scores.json")
    s.add_argument("--iterations", type=int, default=10_000, help="bootstrap resamples")
    s.add_argument("--seed", type=int, default=0)
    _dirs(s)

    j = sub.add_parser("judge-sample", help="export a blind sheet of rubric replies for hand grading")
    j.add_argument("--run-ids", type=_csv, required=True)
    j.add_argument("--n", type=int, default=50)
    j.add_argument("--seed", type=int, default=0)
    j.add_argument("--out", type=Path, default=Path("results/judge_calibration.csv"))
    _dirs(j)

    x = sub.add_parser("export", help="export scores.json + tasks to the JSON file the website reads")
    x.add_argument("--run-id", required=True)
    x.add_argument("--out", type=Path, default=Path("site/data/leaderboard.json"))
    _dirs(x)

    rp = sub.add_parser("report", help="write analysis.md (leaderboard, categories, languages, failures) from scores.json")
    rp.add_argument("--run-id", required=True)
    rp.add_argument("--out", type=Path, default=Path("analysis.md"))
    rp.add_argument("--readme", type=Path, default=None, help="refresh the headline block between the headline markers")
    rp.add_argument("--launch-dir", type=Path, default=None, help="also write linkedin.md and x-thread.md drafts here")
    _dirs(rp)

    a = sub.add_parser("judge-agree", help="compare the judge with your hand grades")
    a.add_argument("--grades", type=Path, required=True, help="the sheet with human_score filled in")
    a.add_argument("--judge", required=True)
    a.add_argument("--out", type=Path, default=None)
    _dirs(a)
    return p


def _cmd_run(args, adapter_factory) -> int:
    problems = validate_dir(args.data_dir)
    if problems:
        print("Dataset is invalid, refusing to run:", file=sys.stderr)
        for m in problems[:10]:
            print("  " + m, file=sys.stderr)
        return 1
    try:
        categories = resolve_categories(args.categories)
        settings = Settings(temperature=TEMPERATURE)
        adapters = [adapter_factory(m, settings) for m in args.models]
    except (ValueError, AdapterError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    tasks = load_tasks(args.data_dir, categories, limit_per_category=args.limit)
    if not tasks:
        print("No verified tasks match. Set \"verified\": true on tasks you have checked by hand, then retry.")
        return 0

    print(f"Running {len(args.models)} model(s) on {len(tasks)} verified task(s)")
    summary = run(adapters, tasks, ResponseCache(args.cache_dir), args.results_dir,
                  run_id=args.run_id, log=lambda m: print("  " + m))
    print(f"Run {summary.run_id}: {summary.total} responses "
          f"({summary.api_calls} API calls, {summary.cache_hits} from cache, {summary.errors} errors)")
    print(f"Saved to {summary.out_dir / 'responses.jsonl'}")
    return 1 if summary.errors else 0


def _make_judge(spec: str, cache_dir: Path, adapter_factory) -> Judge:
    return Judge(adapter_factory(spec, Settings(temperature=TEMPERATURE)), ResponseCache(cache_dir))


def _cmd_score(args, adapter_factory) -> int:
    run_dir = args.results_dir / args.run_id
    if not (run_dir / "responses.jsonl").exists():
        print(f"error: {run_dir / 'responses.jsonl'} not found", file=sys.stderr)
        return 2
    try:
        judge = _make_judge(args.judge, args.cache_dir, adapter_factory) if args.judge else None
        validation = None
        if args.judge_agreement:
            v = json.loads(args.judge_agreement.read_text(encoding="utf-8"))
            validation = {"file": args.judge_agreement.name, "judge": v["judge"], "n": v["agreement"]["n"],
                          "exact_agreement": v["agreement"]["exact_agreement"], "passed": v["passed"]}
            if judge and v["judge"] != judge.name:
                print(f"warning: agreement was measured for {v['judge']}, not {judge.name}", file=sys.stderr)
        report = score_run(run_dir, load_task_map(args.data_dir), judge=judge, skip_rubric=args.skip_rubric,
                           iterations=args.iterations, seed=args.seed, judge_validation=validation)
    except (ValueError, AdapterError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if judge and not validation:
        print("warning: the judge has not been validated against hand grades (see judge-sample / judge-agree)")
    elif validation and not validation["passed"]:
        print("warning: the judge FAILED validation; rubric scores should not be trusted yet")
    for name, m in report["models"].items():
        o = m["overall"]
        line = "no scored items" if o is None else f"{o['mean']:.1%} [{o['ci95'][0]:.1%}, {o['ci95'][1]:.1%}] n={o['n']}"
        print(f"  {name}: {line}")
    print(f"Saved to {run_dir / 'scores.json'}")
    return 0


def _cmd_judge_sample(args, adapter_factory) -> int:
    try:
        items, available = sample_items(args.results_dir, args.run_ids, load_task_map(args.data_dir),
                                        args.n, args.seed)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not items:
        print("No rubric replies found in those runs.")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_sheet(items, args.out)
    print(f"Wrote {len(items)} items to {args.out}. Fill in human_score (0, 1 or 2), then run judge-agree.")
    if available < args.n:
        print(f"warning: only {available} rubric replies exist, fewer than the {args.n} requested. "
              "Add rubric tasks or more models/runs for a meaningful agreement estimate.")
    return 0


def _cmd_judge_agree(args, adapter_factory) -> int:
    try:
        graded, blank = read_grades(args.grades)
        judge = _make_judge(args.judge, args.cache_dir, adapter_factory)
        result = run_agreement(graded, judge, load_task_map(args.data_dir))
    except (ValueError, AdapterError, OSError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    out = args.out or args.grades.with_suffix(".agreement.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    st = result["agreement"]
    print(result["verdict"])
    kappa = st["quadratic_weighted_kappa"]
    print(f"  exact {st['exact_agreement']:.1%} (95% CI {st['exact_ci95'][0]:.0%}-{st['exact_ci95'][1]:.0%}), "
          f"within one {st['within_one']:.1%}, weighted kappa {'n/a' if kappa is None else f'{kappa:.2f}'}")
    if blank:
        print(f"  {blank} row(s) had no human_score and were skipped")
    print(f"Saved to {out}")
    return 0 if result["passed"] else 3


def _cmd_export(args, adapter_factory) -> int:
    run_dir = args.results_dir / args.run_id
    if not (run_dir / "scores.json").exists():
        print(f"error: {run_dir / 'scores.json'} not found; run `bharatbench score` first", file=sys.stderr)
        return 2
    payload = write_export(run_dir, args.data_dir, args.out)
    print(f"Exported {len(payload['models'])} model(s), {payload['totals']['scored_tasks']} scored task(s) to {args.out}")
    return 0


def _cmd_report(args, adapter_factory) -> int:
    run_dir = args.results_dir / args.run_id
    if not (run_dir / "item_scores.jsonl").exists():
        print(f"error: {run_dir / 'item_scores.jsonl'} not found; run `bharatbench score` first", file=sys.stderr)
        return 2
    write_analysis(run_dir, args.data_dir, args.out)
    print(f"Wrote {args.out}")
    if args.readme or args.launch_dir:
        facts = compute_facts(json.loads((run_dir / "scores.json").read_text(encoding="utf-8")))
        if args.readme:
            update_readme(args.readme, facts)
            print(f"Updated headline in {args.readme}")
        if args.launch_dir:
            write_launch(facts, args.launch_dir)
            print(f"Wrote launch drafts to {args.launch_dir}")
    return 0


def main(argv: list[str] | None = None, adapter_factory=build_adapter) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv()  # API keys come only from .env / the environment
    handler = {"run": _cmd_run, "score": _cmd_score, "judge-sample": _cmd_judge_sample,
               "judge-agree": _cmd_judge_agree, "export": _cmd_export, "report": _cmd_report}[args.command]
    return handler(args, adapter_factory)


if __name__ == "__main__":
    raise SystemExit(main())
