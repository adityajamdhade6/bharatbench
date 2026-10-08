# BharatBench site

Next.js (App Router) + Tailwind, built as a static export (`out/`). All numbers come from `data/leaderboard.json`; nothing is hard-coded.

## Update the data

From the repo root, after a run has been scored:

```bash
uv run bharatbench score --run-id <run_id> --skip-rubric        # writes results/<run_id>/scores.json
uv run bharatbench export --run-id <run_id>                     # writes site/data/leaderboard.json
```

Commit `site/data/leaderboard.json`; pushing it redeploys the site.

## Develop

```bash
cd site
npm install
npm run dev        # http://localhost:3000
npm test           # unit tests for sorting, formatting and the Hinglish-gap maths
npm run build      # static export into out/
```

## Deploy on Vercel

1. Push the repository to GitHub.
2. In Vercel: **Add New → Project**, import the repository.
3. Set **Root Directory** to `site`. Vercel detects Next.js; leave the build command (`next build`) and let it use the `out` output.
4. Deploy. Every push to the main branch redeploys.
