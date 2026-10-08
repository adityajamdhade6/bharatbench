# Contributing to BharatBench

Thank you for helping. The most valuable contributions are **new tasks**, **corrections to existing ones**, and **models to evaluate**. Code is MIT-licensed and data is CC BY 4.0; by contributing you agree your contribution is released under the same terms.

## Ground rules

- **Never invent answers.** Every task needs a source or a worked solution that someone else can check.
- **Synthetic only.** No real names, phone numbers, Aadhaar/PAN/GSTIN, account numbers or real documents. Make them up and label documents "SYNTHETIC".
- **No secrets.** Never commit API keys; they live only in `.env`, which is git-ignored.
- **Tests never call a real API.** Use a fake adapter or `httpx.MockTransport`.

## Add or fix a task

Tasks live in `data/*.jsonl`, one JSON object per line, one file per category. A task looks like this:

```json
{"id": "gst-021", "category": "gst_tax",
 "prompt": "A shop sells a bag for ₹2,000 before tax. GST is 18%. What total does the customer pay? Reply with only the number (rupees, no commas or ₹ symbol).",
 "language": "en", "answer_type": "numeric", "reference_answer": 2360, "tolerance": 0.01,
 "worked_solution": "GST = 2,000 × 18% = ₹360. Total = ₹2,360.",
 "difficulty": "easy", "verified": false}
```

| Field | Notes |
|---|---|
| `id` | Next free number in the category: `gst-`, `hin-`, `doc-`, `law-`, `pay-` plus three digits |
| `category` | `gst_tax`, `hinglish_support`, `documents`, `law_policy`, `payments_banking` |
| `language` | `en`, `hi` (Devanagari) or `hinglish` (Hindi in Roman letters) |
| `answer_type` | `exact` (string), `numeric` (number), `extraction` (object of fields), `rubric` (list of criteria) |
| `worked_solution` / `source_url` | At least one. GST/tax tasks need the full calculation; law tasks need an official URL |
| `verified` | **Always submit `false`.** Maintainers set it after checking |

Guidelines for good tasks:

1. **State the rules in the prompt** for calculations (rates, slabs, thresholds), so the task tests reasoning, not memory of rules that change.
2. **Ask for a bare answer** for `exact` and `numeric` tasks ("Reply with only the number", "Reply in the form T+N"), because scoring is strict about format.
3. **One unambiguous answer.** If two reasonable readings exist, fix the prompt.
4. **Cite the primary source** (the Act, rule, circular or official FAQ), and quote the provision you relied on in `worked_solution`.
5. For extraction tasks, make sure every reference value appears in the prompt text.

Then check it:

```bash
uv run python -m bharatbench.validate     # fails on missing fields or duplicate ids
uv run pytest
```

and open a pull request. In the PR, say how you checked the answer (recomputed by hand, read the Act, and so on). A reviewer will re-derive it independently before setting `verified` to `true`.

### Keeping a task out of the public set

If you would rather your tasks not be published, open an issue to arrange a private submission. Tasks added to the private held-out set are never released with their answers; see [docs/HELDOUT.md](docs/HELDOUT.md).

## Report a wrong answer

Open an issue with the task id, what you believe the correct answer is, and a source. Corrections are recorded in [data/VERIFICATION.md](data/VERIFICATION.md).

## Add a model or provider

See "Add a model" in the [README](README.md#add-a-model). New providers need an adapter, a registry entry, an entry in `.env.example`, and tests that use mocked HTTP.

## Development

```bash
uv sync
uv run pytest                      # Python tests
cd site && npm install && npm test # site tests
```

Keep changes small. For anything touching more than three files, describe the plan in the PR first.
