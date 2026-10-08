# BharatBench
A public benchmark measuring how well LLMs handle real Indian tasks, with a leaderboard website.

## Task categories (5)
1. GST & tax math (GST slabs, invoices, TDS, simple income tax)
2. Hinglish & Hindi customer support (understand and reply correctly)
3. Indian documents (extract fields from invoices, rent agreements, bank statements; synthetic only)
4. Indian law & policy (consumer rights, RTI, labour basics; factual, sourced)
5. Payments & banking support (UPI failures, refunds, KYC; no real personal data)

## Stack
- Python 3.11, uv for packages, pytest for tests
- Models called through one adapter layer: Gemini (AI Studio), Groq, OpenRouter; API keys only from .env
- Data in JSONL; results in results/<run_id>/
- Website: Next.js static export, deployed on Vercel

## Rules
- Small steps. Show a plan before any change touching more than 3 files.
- Every module gets tests. Run tests before saying a task is done.
- Never invent dataset answers. Every task has a source or a worked solution I can check.
- Never commit API keys or real personal data.
- Cache every model response so re-runs cost nothing.
- When unsure, ask me instead of guessing.
