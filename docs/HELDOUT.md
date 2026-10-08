# The held-out set

## What it is

BharatBench has two parts:

| Part | Tasks | Share | Where |
|---|---:|---:|---|
| Public set | 100 | 80% | this repository, with reference answers |
| Held-out set | 25 | 20% | a private repository; never published |

The held-out set has the same schema, the same five categories (5 tasks each), an intended mix of answer types, languages and difficulty, and the same scoring. It uses new scenarios and new numbers, so nothing in it is a rewording of a public task.

## Why

Anything published on the internet can end up in a model's training data. If a model has seen a task's answer, a high score on that task says little about the model. The held-out set is a check: **if a model does much better on the public tasks than on the held-out tasks, it may have seen the public ones.** Comparing the two sets per model is the contamination test.

## What we promise

- Held-out tasks and their answers are never published, quoted in public results, or sent to a model provider for anything other than the scoring run itself.
- Only aggregate held-out scores (per model, per category) are published.
- When the held-out set is refreshed, retired tasks may be released publicly and replaced by new ones.

## What this cannot guarantee

Being honest about the limits:

- **Provider logging.** Running a hosted model sends the prompt to its provider, which may log it, and free API tiers commonly allow providers to use submitted prompts to improve their products. The held-out set therefore degrades a little with every model evaluated, and more on free tiers. Prefer paid or no-training API terms for held-out runs, and refresh the set periodically.
- **It has already been sent to a free tier once.** The first workflow test ran the held-out tasks through two models on the Gemini API free tier. If Google's free-tier terms allow training on that content, those 25 tasks are not guaranteed clean; treat the first held-out results as a workflow check, and consider replacing the set before relying on it for contamination claims.
- **The first release was fully public.** This repository briefly contained all 100 public tasks and answers before the held-out set existed. The held-out tasks were written *after* that and have never been public, so they are unaffected. Nobody can claim the public 100 are held out.
- **Difficulty is not yet matched.** In the first workflow test the two models scored *higher* on the held-out tasks than on the public ones, so the held-out set is easier. A contamination test only works when the two sets are equally hard (the signal is public accuracy well above held-out accuracy), so the held-out set needs more medium and hard tasks before it can be used that way.
- **Size.** 25 tasks is small: held-out scores have wide confidence intervals, so only a large public-versus-held-out gap is meaningful.
- **Verification.** Like the public set, the held-out tasks were checked with AI assistance, not by independent human reviewers.

## Running it (maintainers)

The held-out tasks use the same format, so the normal runner works; point it at the private data and keep the results private too:

```bash
uv run bharatbench run --data-dir ../bharatbench-heldout/data \
  --results-dir ../bharatbench-heldout/results --models gemini-flash-lite
uv run bharatbench score --run-id <run_id> --skip-rubric \
  --data-dir ../bharatbench-heldout/data --results-dir ../bharatbench-heldout/results
```

Do not commit held-out responses, prompts or scores' item files to this repository. The response cache (`.cache/`) is git-ignored.

## Evaluating your model on it

Open an issue with the model name and how to call it. A maintainer can run it and publish the aggregate held-out score; we will not share the tasks.

## Status

The held-out set exists and has been run on two Gemini models, only to test the workflow (see the free-tier and difficulty caveats above). The published leaderboard shows public-set results only; no held-out scores are published yet.
