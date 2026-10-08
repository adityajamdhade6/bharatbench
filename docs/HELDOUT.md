# The held-out set

## What it is

BharatBench has two parts:

| Part | Tasks | Share | Where |
|---|---:|---:|---|
| Public set | 100 | 80% | this repository, with reference answers |
| Held-out set | 25 | 20% | a private repository; never published |

The held-out set has the same schema, the same five categories (5 tasks each), the same scoring, and a similar mix of languages and answer types. A further private **reserve** of 15 tasks is kept to replace held-out tasks when they become exposed.

## Why

Anything published on the internet can end up in a model's training data. If a model has seen a task's answer, a high score on that task says little about the model. The held-out set is a check: **if a model does much better on the public tasks than on the held-out tasks, it may have seen the public ones.** Comparing the two sets per model is the contamination test.

## How the held-out tasks were made (difficulty matching)

A contamination test is only fair if the two sets are equally hard. So each held-out task is a **twin** of a public task: the same kind of question with new numbers, names or provisions. For each public task we know how many of the seven evaluated models got it wrong, and the twins were chosen so that their public counterparts have about the same failure rate as the public set as a whole. Across the 25 held-out tasks, the twinned public tasks averaged 1.08 failures out of 7 models, against 1.11 across all 94 scored public tasks. This matches difficulty *by design*; it has not yet been measured on the held-out tasks themselves, because they have not been run on any model.

## What we promise

- Held-out tasks and their answers are never published, quoted in public results, or sent to a model provider for anything other than a scoring run.
- Only aggregate held-out scores (per model, per category) are published.
- When tasks are retired from the held-out set, they may be released publicly and replaced from the reserve.

## What this cannot guarantee

- **Provider logging.** Running a hosted model sends the prompt to its provider, which may log it, and free API tiers commonly allow providers to use submitted prompts to improve their products. The held-out set therefore degrades a little with every model evaluated, and more on free tiers. Prefer paid or no-training API terms, or locally hosted open-weights models, for held-out runs, and refresh the set from the reserve periodically.
- **An earlier draft was exposed.** A first, easier draft of 25 held-out tasks was run on two models on the Gemini API free tier as a workflow test. That draft has been retired and replaced; the current set has not been sent to any provider.
- **The first release was fully public.** This repository contained all 100 public tasks and answers before the held-out set existed. The held-out tasks were written *after* that and have never been public. Nobody can claim the public 100 are held out.
- **Twins share structure.** Because held-out tasks twin public ones, a model that memorised the public *templates* (not just the answers) could gain a little on them; this makes the contamination test conservative, not airtight.
- **Size.** 25 tasks is small: held-out scores have wide confidence intervals, so only a large public-versus-held-out gap is meaningful.
- **Verification.** Like the public set, the held-out tasks were checked with AI assistance, not by independent human reviewers.

## Running it (maintainers)

The held-out tasks use the same format, so the normal runner works; point it at the private data and keep the results private too:

```bash
uv run bharatbench run --data-dir ../bharatbench-heldout/data \
  --results-dir ../bharatbench-heldout/results --models <model>
uv run bharatbench score --run-id <run_id> --skip-rubric \
  --data-dir ../bharatbench-heldout/data --results-dir ../bharatbench-heldout/results
```

Do not commit held-out responses, prompts or item scores to this repository. The response cache (`.cache/`) is git-ignored.

## Evaluating your model on it

Open an issue with the model name and how to call it. A maintainer can run it and publish the aggregate held-out score; we will not share the tasks.

## Status

The current held-out set exists and has **not yet been run on any model**. No held-out scores are published. The published leaderboard shows public-set results only.
