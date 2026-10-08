# BharatBench

BharatBench is a public benchmark that measures how well LLMs handle real Indian tasks, with a leaderboard website. It covers five categories: GST and tax math, Hinglish and Hindi customer support, Indian documents (synthetic only), Indian law and policy, and payments and banking support. Every task carries a source or a worked solution that can be checked.

## Setup

1. Install [uv](https://docs.astral.sh/uv/).
2. Install dependencies: `uv sync`
3. Copy `.env.example` to `.env` and add your Gemini (AI Studio), Groq and OpenRouter API keys. `.env` is git-ignored.
4. Run the tests: `uv run pytest`

## Dataset

Tasks live in `data/*.jsonl` (schema: `data/schema/task.schema.json`). Every task starts with `"verified": false`; only tasks you have checked by hand and flipped to `true` are ever sent to a model.

```bash
uv run python -m bharatbench.validate --expect-per-category 20
```

## Running the benchmark

```bash
uv run bharatbench run --models gemini-flash,llama-3.3-70b --categories gst,hinglish --limit 20
```

- Categories: `gst`, `hinglish`, `docs`, `law`, `payments` (default: all). `--limit` is per category.
- Models: aliases from `bharatbench.adapters.MODEL_ALIASES`, or `provider:model-id` (providers: `gemini`, `groq`, `openrouter`).
- Temperature is always 0. Raw responses go to `results/<run_id>/responses.jsonl`.
- Responses are cached in `.cache/responses/` (git-ignored), so re-running the same models and prompts makes no API calls.

## Scoring

```bash
uv run bharatbench score --run-id <run_id> --judge <judge-model>   # or --skip-rubric
```

Writes `results/<run_id>/scores.json` (per-model and per-category mean score with a 95% bootstrap CI) and `item_scores.jsonl` (every item's score and reason).

- `exact`: normalised match (case, spaces, punctuation ignored).
- `numeric`: final number in the reply, ₹/commas/lakh/crore understood, ±0.5% (or the task's own `tolerance` if larger).
- `extraction`: share of reference fields that match.
- `rubric`: an LLM judge scores 0-2 against the task's criteria and gives a reason; the score is stored as judge/2.

### Validating the judge before trusting it

```bash
uv run bharatbench judge-sample --run-ids <run_id>[,<run_id>] --n 50 --out results/judge_calibration.csv
# grade the human_score column (0, 1 or 2) by hand, then:
uv run bharatbench judge-agree --grades results/judge_calibration.csv --judge <judge-model>
uv run bharatbench score --run-id <run_id> --judge <judge-model> --judge-agreement results/judge_calibration.agreement.json
```

The sheet hides the judge's scores. `judge-agree` exits with code 3 if exact agreement is below 80%; fix the rubric before trusting the judge. Use a judge from a different model family than the models being tested.

## Website

The leaderboard site lives in `site/` (Next.js static export). After scoring a run:

```bash
uv run bharatbench export --run-id <run_id>   # -> site/data/leaderboard.json
cd site && npm install && npm run dev
```

See `site/README.md` for deployment.

## Layout

- `data/` task data (JSONL)
- `src/bharatbench/` adapters, scoring, runner
- `tests/` pytest tests
- `results/<run_id>/` run outputs (response caches are git-ignored)
- `site/` leaderboard website (Next.js static export)
