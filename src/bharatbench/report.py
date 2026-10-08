"""Write analysis.md and the launch drafts. Every number comes from results/<run_id>/scores.json."""
from __future__ import annotations

import json
from pathlib import Path

from .export import CATEGORY_INFO, LANGUAGE_LABELS
from .scoring.run import load_task_map
from .validate import CATEGORY_PREFIX


def _label(model_id: str) -> str:
    return model_id.split("/", 1)[1].split("/")[-1]


def fmt_distinct(values: list[float]) -> list[str]:
    """Fewest decimals (1..4) at which different values stay different; equal values stay equal."""
    for d in range(1, 5):
        out = [f"{v * 100:.{d}f}" for v in values]
        clash = any(values[i] != values[j] and out[i] == out[j]
                    for i in range(len(values)) for j in range(i + 1, len(values)))
        if not clash or d == 4:
            return [f"{s}%" for s in out]
    return []


def pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}%"


def compute_facts(scores: dict) -> dict:
    """All headline numbers, derived only from scores.json."""
    models = scores["models"]
    ranking = sorted(({"id": k, "label": _label(k), "mean": m["overall"]["mean"], "lo": m["overall"]["ci95"][0],
                       "hi": m["overall"]["ci95"][1], "n": m["overall"]["n"],
                       "excluded": m["api_errors_excluded"]} for k, m in models.items() if m["overall"]),
                      key=lambda r: (-r["mean"], r["label"]))
    top = ranking[0]
    overlapping_top = [r["label"] for r in ranking[1:] if r["hi"] >= top["lo"] and top["hi"] >= r["lo"]
                       and r["lo"] <= top["hi"]]
    cats = sorted({c for m in models.values() for c in m["categories"]}, key=list(CATEGORY_PREFIX).index)
    cat_avg = {c: sum(m["categories"][c]["mean"] for m in models.values() if c in m["categories"])
               / sum(1 for m in models.values() if c in m["categories"]) for c in cats}
    cat_n = {c: next(m["categories"][c]["n"] for m in models.values() if c in m["categories"]) for c in cats}
    cells = [(m["categories"][c]["mean"], k, c) for k, m in models.items() for c in m["categories"]]
    low = min(cells)
    lang = {k: {l: (v["mean"], v["n"], v["ci95"]) for l, v in m["languages"].items()} for k, m in models.items()}
    both = [k for k, v in lang.items() if "en" in v and "hinglish" in v]
    gaps = {k: lang[k]["en"][0] - lang[k]["hinglish"][0] for k in both}
    return {
        "run_id": scores["run_id"], "generated": scores["generated"], "iterations": scores["bootstrap"]["iterations"],
        "ranking": ranking, "top": top, "bottom": ranking[-1], "overlapping_top": overlapping_top,
        "categories": cats, "cat_avg": cat_avg, "cat_n": cat_n,
        "hardest": min(cat_avg, key=cat_avg.get), "easiest": max(cat_avg, key=cat_avg.get),
        "lowest_cell": {"value": low[0], "model": _label(low[1]), "category": low[2]},
        "language": lang, "gaps": gaps,
        "hinglish_lower_count": sum(1 for g in gaps.values() if g > 0), "gap_models": len(gaps),
        "mean_en": sum(lang[k]["en"][0] for k in both) / len(both) if both else None,
        "mean_hinglish": sum(lang[k]["hinglish"][0] for k in both) / len(both) if both else None,
        "n_en": next((lang[k]["en"][1] for k in both), None), "n_hinglish": next((lang[k]["hinglish"][1] for k in both), None),
        "n_models": len(ranking),
    }


def pick_failures(items: list[dict], responses: dict, tasks: dict, n: int = 10) -> list[dict]:
    """Deterministic, varied: cycle through categories, prefer tasks many models failed, one per task."""
    fails = [i for i in items if i["score"] is not None and i["score"] < 1]
    by_task: dict[str, list[dict]] = {}
    for i in fails:
        by_task.setdefault(i["task_id"], []).append(i)
    by_cat: dict[str, list[str]] = {}
    for tid in sorted(by_task, key=lambda t: (-len(by_task[t]), t)):
        by_cat.setdefault(tasks[tid]["category"], []).append(tid)
    order = [c for c in CATEGORY_PREFIX if c in by_cat]
    chosen: list[dict] = []
    used_models: dict[str, int] = {}
    while len(chosen) < n and any(by_cat.values()):
        for c in order:
            if by_cat.get(c) and len(chosen) < n:
                tid = by_cat[c].pop(0)
                cand = sorted(by_task[tid], key=lambda i: (used_models.get(i["model"], 0), i["model"]))[0]
                used_models[cand["model"]] = used_models.get(cand["model"], 0) + 1
                chosen.append({**cand, "n_failed": len(by_task[tid])})
    return chosen


def _answer_text(ref) -> str:
    if isinstance(ref, str):
        return ref
    return json.dumps(ref, ensure_ascii=False)


def _clip(text: str, n: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def build_analysis(run_dir: Path, data_dir: Path) -> str:
    run_dir = Path(run_dir)
    scores = json.loads((run_dir / "scores.json").read_text(encoding="utf-8"))
    f = compute_facts(scores)
    tasks = load_task_map(data_dir)
    items = [json.loads(l) for l in (run_dir / "item_scores.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    resp = {}
    for l in (run_dir / "responses.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(l)
        resp[(f"{r['provider']}/{r['model']}", r["task_id"])] = r["response"]
    L: list[str] = []
    A = L.append
    A("# BharatBench analysis")
    A("")
    A(f"Run `{f['run_id']}`, scored {f['generated'][:10]}. Every number below is read from "
      f"`results/{f['run_id']}/scores.json`; scores are the mean item score (0 to 1) shown as a percentage, "
      f"with 95% percentile-bootstrap intervals ({f['iterations']:,} resamples over tasks). "
      "Rankings use the unrounded scores; displayed decimals are added wherever rounding would make different scores look equal.")
    A("")
    A("## Overall leaderboard")
    A("")
    texts = fmt_distinct([r["mean"] for r in f["ranking"]])
    A("| Rank | Model | Score | 95% interval | Tasks scored |")
    A("|---:|---|---:|---:|---:|")
    rank, prev = 0, None
    for i, (r, t) in enumerate(zip(f["ranking"], texts), 1):
        rank = rank if r["mean"] == prev else i
        prev = r["mean"]
        A(f"| {rank} | {r['label']} | {t} | {pct(r['lo'])} to {pct(r['hi'])} | {r['n']} |")
    A("")
    top = f["top"]
    if f["overlapping_top"]:
        A(f"The top model, {top['label']}, cannot be separated from: {', '.join(f['overlapping_top'])} "
          "(their 95% intervals overlap with its interval). Treat the order among them as unsettled.")
    else:
        A(f"The top model, {top['label']}, is separated from every other model by non-overlapping intervals.")
    A("")
    ex = [r for r in f["ranking"] if r["excluded"]]
    if ex:
        A("Excluded replies (no answer could be obtained, so not counted as wrong): "
          + "; ".join(f"{r['label']} {r['excluded']}" for r in ex) + ".")
        A("")

    A("## Per category")
    A("")
    labels = [CATEGORY_INFO[c][0] for c in f["categories"]]
    A("| Model | " + " | ".join(labels) + " |")
    A("|---|" + "---:|" * len(labels))
    for r in f["ranking"]:
        m = scores["models"][r["id"]]["categories"]
        A(f"| {r['label']} | " + " | ".join(pct(m[c]["mean"]) if c in m else "–" for c in f["categories"]) + " |")
    A("| **Average of models** | " + " | ".join(f"**{pct(f['cat_avg'][c])}**" for c in f["categories"]) + " |")
    A("| *Tasks* | " + " | ".join(f"*{f['cat_n'][c]}*" for c in f["categories"]) + " |")
    A("")
    lc = f["lowest_cell"]
    A(f"**Hardest category:** {CATEGORY_INFO[f['hardest']][0]}, with the lowest average across the {f['n_models']} models "
      f"({pct(f['cat_avg'][f['hardest']])}). **Easiest:** {CATEGORY_INFO[f['easiest']][0]} ({pct(f['cat_avg'][f['easiest']])}). "
      f"The single lowest model-category score is {lc['model']} on {CATEGORY_INFO[lc['category']][0]} ({pct(lc['value'])}).")
    A("")

    A("## English, Hindi and Hinglish")
    A("")
    A("| Model | " + " | ".join(f"{LANGUAGE_LABELS[l]} (n)" for l in ("en", "hi", "hinglish")) + " | English minus Hinglish |")
    A("|---|---:|---:|---:|---:|")
    for r in f["ranking"]:
        lg = f["language"][r["id"]]
        cells = [f"{pct(lg[l][0])} ({lg[l][1]})" if l in lg else "–" for l in ("en", "hi", "hinglish")]
        g = f["gaps"].get(r["id"])
        sign = "" if g is None else ("+" if g > 0 else "−" if g < 0 else "")
        A(f"| {r['label']} | " + " | ".join(cells) + f" | {'–' if g is None else f'{sign}{abs(g) * 100:.1f} pp'} |")
    A("")
    if f["gap_models"]:
        diff = f["mean_en"] - f["mean_hinglish"]
        A(f"Averaged over the {f['gap_models']} models, English accuracy is {pct(f['mean_en'])} and Hinglish accuracy is "
          f"{pct(f['mean_hinglish'])}, a difference of {abs(diff) * 100:.1f} percentage points "
          f"({'English higher' if diff > 0 else 'Hinglish higher' if diff < 0 else 'no difference'}). "
          f"Hinglish is lower than English for {f['hinglish_lower_count']} of {f['gap_models']} models.")
        A("")
    A("Read this with care: the tasks are different questions in each language, not translations. Hinglish and Hindi tasks "
      f"are mostly customer-support classification and extraction ({f['n_hinglish']} Hinglish tasks scored per model), "
      "while English tasks include the harder calculations, so a language gap here is confounded with task type. "
      "The Hindi sample is small.")
    A("")

    A("## Ten example failures")
    A("")
    A("Selected by rule, not by hand: cycle through the categories, take the tasks that the most models failed, one model per task. "
      "Each shows the model's answer next to the reference answer. Some are format failures rather than wrong facts: the "
      "scorer is strict, so an extra word in an extracted field or a long explanation where a bare answer was requested scores zero.")
    A("")
    for k, fl in enumerate(pick_failures(items, resp, tasks), 1):
        t = tasks[fl["task_id"]]
        A(f"### {k}. {fl['task_id']} · {CATEGORY_INFO[t['category']][0]} · {_label(fl['model'])}")
        A("")
        A(f"- **Prompt:** {_clip(t['prompt'], 240)}")
        A(f"- **Model answer:** {_clip(resp.get((fl['model'], fl['task_id'])) or '', 300)}")
        A(f"- **Correct answer:** {_clip(_answer_text(t['reference_answer']), 300)}")
        A(f"- **Scorer:** {fl['detail']}; {fl['n_failed']} of {f['n_models']} models failed this task.")
        A("")
    return "\n".join(L).rstrip() + "\n"


def write_analysis(run_dir: Path, data_dir: Path, out: Path) -> str:
    text = build_analysis(run_dir, data_dir)
    Path(out).write_text(text, encoding="utf-8")
    return text


# ---------------------------------------------------------------- launch text (numbers from scores.json only)
README_START, README_END = "<!-- headline:start -->", "<!-- headline:end -->"
REPO_URL = "https://github.com/adityajamdhade6/bharatbench"
SITE_URL = "https://bharatbench.vercel.app/"


RULE_HEAVY = {"gst_tax", "law_policy", "payments_banking"}


def rule_heavy_is_hardest(f: dict) -> bool:
    """True only when the three lowest-scoring categories are exactly the rule-heavy ones."""
    return set(sorted(f["cat_avg"], key=f["cat_avg"].get)[:3]) == RULE_HEAVY


def headline_points(f: dict) -> list[str]:
    """The headline findings as plain sentences. Every figure is read from `compute_facts`."""
    r = f["ranking"]
    top, bottom = f["top"], f["bottom"]
    tasks = max(x["n"] for x in r)
    cats = sorted(f["cat_avg"], key=f["cat_avg"].get)
    name = lambda c: CATEGORY_INFO[c][0]
    top_note = f" (on {top['n']} of {tasks} tasks; the rest could not be obtained)" if top["n"] < tasks else ""
    pts = [
        f"Scores range from {bottom['label']} at {pct(bottom['mean'])} to {top['label']} at {pct(top['mean'])}{top_note}, "
        f"a {(top['mean'] - bottom['mean']) * 100:.1f}-point spread.",
        f"The top {len(f['overlapping_top']) + 1} models cannot be told apart statistically: their 95% confidence intervals overlap.",
        f"{'The rule-heavy categories are the hard ones. ' if rule_heavy_is_hardest(f) else 'Categories differ widely. '}Average accuracy across models is lowest on {name(cats[0])} ({pct(f['cat_avg'][cats[0]])}), "
        f"{name(cats[1])} ({pct(f['cat_avg'][cats[1]])}) and {name(cats[2])} ({pct(f['cat_avg'][cats[2]])}), "
        f"and highest on {name(cats[-1])} ({pct(f['cat_avg'][cats[-1]])}).",
    ]
    if f["gap_models"]:
        lower = f["hinglish_lower_count"]
        verdict = "There is no consistent Hinglish penalty" if f["mean_hinglish"] >= f["mean_en"] else "Hinglish accuracy is lower than English"
        pts.append(f"{verdict}: Hinglish is lower than English for {lower} of {f['gap_models']} models, and averaged over models English is "
                   f"{pct(f['mean_en'])} against {pct(f['mean_hinglish'])} for Hinglish. The tasks differ by language, so this is not a like-for-like comparison.")
    lc = f["lowest_cell"]
    pts.append(f"The weakest single result is {lc['model']} on {name(lc['category'])}, at {pct(lc['value'])}.")
    return pts


def headline_block(f: dict) -> str:
    tasks = max(x["n"] for x in f["ranking"])
    lead = f"{f['n_models']} models were scored on {tasks} verified tasks."
    body = "\n".join(f"- {p}" for p in [lead] + headline_points(f))
    return f"{README_START}\n{body}\n\n*Run `{f['run_id']}`; all figures are read from `results/{f['run_id']}/scores.json`. Details: [analysis.md](analysis.md).*\n{README_END}"


def update_readme(readme: Path, f: dict) -> None:
    text = Path(readme).read_text(encoding="utf-8")
    if README_START not in text or README_END not in text:
        raise ValueError(f"{readme} has no {README_START} ... {README_END} block")
    head, rest = text.split(README_START, 1)
    _, tail = rest.split(README_END, 1)
    Path(readme).write_text(head + headline_block(f) + tail, encoding="utf-8")


def linkedin_post(f: dict) -> str:
    pts = headline_points(f)
    tasks = max(x["n"] for x in f["ranking"])
    return f"""I built BharatBench: a public benchmark of how well LLMs handle real Indian tasks.

It covers GST and tax math, Hinglish and Hindi customer support, extracting fields from invoices, rent agreements and bank statements, consumer/RTI/labour law, and UPI/banking rules. Every task has a worked solution or an official source link, and every document is synthetic.

First results ({f['n_models']} models, {tasks} verified tasks):

• {pts[0]}
• {pts[1]}
• {pts[2]}
• {pts[3] if f['gap_models'] else pts[-1]}

What I would not claim: the tasks are few per category, so the confidence intervals are wide; the answer checks were done with AI assistance rather than by independent human reviewers (a human spot-check is still pending); and a further set of tasks is kept private so models cannot simply be trained on the answers.

Code is MIT, data is CC BY 4.0. If you work on Indian-language or fintech AI, I would love tasks, corrections and models to add.

Repo: {REPO_URL}
Leaderboard: {SITE_URL}

#LLM #India #Hinglish #Benchmark #AIEvaluation"""


def x_thread(f: dict) -> list[str]:
    r, top, bottom = f["ranking"], f["top"], f["bottom"]
    tasks = max(x["n"] for x in r)
    cats = sorted(f["cat_avg"], key=f["cat_avg"].get)
    name = lambda c: CATEGORY_INFO[c][0]
    lc = f["lowest_cell"]
    t = [
        f"How well do LLMs handle real Indian tasks? I built BharatBench: GST and tax math, Hinglish support, invoices and bank statements, Indian law, UPI and banking rules. {f['n_models']} models, {tasks} verified tasks. A thread. 🧵",
        f"The spread is wide: {bottom['label']} scores {pct(bottom['mean'])}, {top['label']} scores {pct(top['mean'])}"
        + (f" (on {top['n']} of {tasks} tasks)." if top["n"] < tasks else "."),
        f"But the top {len(f['overlapping_top']) + 1} models cannot be separated: their 95% confidence intervals overlap. With only {min(f['cat_n'].values())} to {max(f['cat_n'].values())} tasks per category, treat the order among them as unsettled.",
        f"{'The hard part looks like rules, not language. ' if rule_heavy_is_hardest(f) else 'Categories differ widely. '}Average accuracy: {name(cats[0])} {pct(f['cat_avg'][cats[0]])}, {name(cats[1])} {pct(f['cat_avg'][cats[1]])}, {name(cats[2])} {pct(f['cat_avg'][cats[2]])}. {name(cats[-1])}: {pct(f['cat_avg'][cats[-1]])}.",
    ]
    if f["gap_models"]:
        t.append(f"Hinglish vs English: Hinglish is lower for {f['hinglish_lower_count']} of {f['gap_models']} models; averaged, {pct(f['mean_hinglish'])} Hinglish vs {pct(f['mean_en'])} English. Different tasks per language, so no clean verdict.")
    t.append(f"Weakest single result: {lc['model']} on {name(lc['category'])}, {pct(lc['value'])}.")
    t.append(f"Caveats: few tasks per category, answer checks were AI-assisted (human spot-check pending), and a private held-out set guards against training on the answers. Code MIT, data CC BY 4.0. Live: {SITE_URL} Code: {REPO_URL}")
    return t


def write_launch(f: dict, out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "linkedin.md").write_text(linkedin_post(f) + "\n", encoding="utf-8")
    thread = x_thread(f)
    (out_dir / "x-thread.md").write_text(
        "\n\n".join(f"**{i}/{len(thread)}** ({len(t)} chars)\n\n{t}" for i, t in enumerate(thread, 1)) + "\n", encoding="utf-8")
