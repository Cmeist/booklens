# BookLens

BookLens is an interactive book discovery and recommendation web app built as a data analytics portfolio project. Users explore books with useful filters, browse popular tags, see explainable similar-book recommendations, and review lightweight dataset analytics.

## Current MVP (complete)

This repo ships a **Supabase-backed MVP** with a committed fixture fallback:

1. Python scripts collect and process book data (`make pipeline-demo`).
2. The pipeline writes processed CSVs locally and committed JSON fixtures under `apps/web/src/data/`.
3. SQL migrations in `supabase/migrations/` define the Postgres schema.
4. `make seed-supabase` loads books, tags, and recommendations into Supabase (server-only `SUPABASE_DB_URL`).
5. The Next.js app reads from Supabase when `NEXT_PUBLIC_SUPABASE_*` env vars are set; otherwise it uses the committed sample JSON.

**Not in scope:** FastAPI, Supabase Auth, Supabase Storage, LiteLLM, or user accounts.

See `docs/PLAN.md` for the phased build plan, `docs/LIVE_DATA_PLAN.md` for live Open Library ingestion, `docs/DEPLOYMENT.md` for Vercel + Modal setup, `supabase/README.md` for database setup, and `docs/DESIGN.md` for product goals.

## Repo structure

```text
booklens/
├── apps/web/              # Next.js + TypeScript frontend (Vercel root)
├── data/
│   ├── raw/               # Generated raw CSVs (Git-ignored)
│   └── processed/         # Generated processed CSVs (Git-ignored)
├── docs/
│   ├── DESIGN.md          # Product and design source of truth
│   ├── PLAN.md            # Implementation phases for Cursor
│   └── LOCAL_DEV_WSL_CURSOR.md
├── scripts/
│   ├── run_pipeline.py    # Demo pipeline (writes sample processed data)
│   ├── collect_openlibrary.py
│   └── seed_supabase.py   # Upsert fixture/processed data into Supabase
├── modal_app.py           # Modal data-refresh jobs
├── supabase/
│   ├── migrations/        # Committed SQL schema
│   └── README.md          # Supabase setup, migrations, and seed workflow
├── .env.example           # Safe to commit (placeholders only)
├── Makefile               # Common local commands
├── pyproject.toml         # Python project (uv)
└── uv.lock
```

Generated outputs under `data/raw/` and `data/processed/` stay out of Git. Committed web fixtures under `apps/web/src/data/*.sample.json` power local dev and Vercel when Supabase is not configured.

## Prerequisites

Develop inside **WSL2 Ubuntu**, not directly under `/mnt/c/...`. Keep the repo on a Linux path such as `~/dev/booklens`.

You need these tools available inside WSL:

- Git
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js and npm (Linux install, e.g. via nvm)

Full setup steps: [`docs/LOCAL_DEV_WSL_CURSOR.md`](docs/LOCAL_DEV_WSL_CURSOR.md).

## Quick start

From the repo root in a WSL terminal:

```bash
# 1. Confirm tools resolve to Linux paths (not /mnt/c/...)
make check-env

# 2. Install Python dependencies
uv sync

# 3. Install frontend dependencies
cd apps/web && npm install && cd ../..

# 4. Run the demo pipeline (no network required)
make pipeline-demo

# 5. Start the Next.js dev server
make web-dev
```

Open [http://localhost:3000](http://localhost:3000) after `make web-dev` starts.

Without Supabase env vars, the app loads the committed sample fixture. Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `.env` (or Vercel) to read live data after migrations and seeding.

## Common commands

From the repo root:

| Command | Purpose |
| --- | --- |
| `make check-env` | Print paths for git, node, npm, python3, and uv |
| `make pipeline-demo` | Run the demo data pipeline |
| `make collect-openlibrary` | Collect real Open Library books (`BOOKLENS_CONTACT_EMAIL` or `CONTACT=...` required) |
| `make pipeline-openlibrary` | Process `data/raw/openlibrary_books.csv` into processed CSVs |
| `make seed-supabase` | Upsert sample JSON into Supabase (`SUPABASE_DB_URL` required) |
| `make web-dev` | Start the Next.js dev server |
| `make web-build` | Production build of the web app |
| `make vercel-deploy` | Deploy `apps/web` to Vercel with `npx vercel --prod` |
| `make modal-deploy` | Deploy the Modal data jobs |
| `make modal-refresh` | Run the Modal Open Library refresh job |
| `make verify` | Run all MVP verification commands (see below) |
| `make status` | Show `git status` |
| `uv run ruff check scripts/` | Lint Python pipeline/seed scripts |

From `apps/web`:

| Command | Purpose |
| --- | --- |
| `npm run dev` | Dev server (same as `make web-dev`) |
| `npm run build` | Production build (same as `make web-build`) |
| `npm run lint` | ESLint |
| `npm run start` | Serve a production build |

Optional live Open Library collection (network required; not needed for the demo pipeline):

```bash
make collect-openlibrary
make pipeline-openlibrary
make seed-supabase SOURCE=csv
```

Defaults collect up to **120** unique works across **10** subjects (`LIMIT_TOTAL` and `SUBJECTS` are overridable). Generated files stay under `data/raw/` and `data/processed/` and are Git-ignored.

Full workflow: [`docs/LIVE_DATA_PLAN.md`](docs/LIVE_DATA_PLAN.md)

## Verification

Run these before deploying or opening a PR:

```bash
make pipeline-demo
uv run ruff check scripts/
cd apps/web && npm run lint
cd apps/web && npm run build
```

Or from the repo root:

```bash
make verify
```

## Environment and secrets

- Copy `.env.example` to `.env` for local-only values. **Never commit `.env`.**
- `.env.example` uses placeholders only and is safe to commit.
- **Browser-safe (Next.js):** `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- **Server-only (seed scripts, never Vercel):** `SUPABASE_DB_URL` (and optional service-role keys for future tooling)
- Do not commit API keys, database URLs, service-role keys, or other secrets.
- **Fixture fallback:** if public Supabase env vars are missing or Supabase fetch fails, the app serves `apps/web/src/data/*.sample.json` and shows a warning banner when appropriate.

Supabase setup: [`supabase/README.md`](supabase/README.md)

## Deploy to Vercel

Full Vercel + Modal setup: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

1. Import the Git repository in [Vercel](https://vercel.com).
2. Set **Root Directory** to `apps/web`.
3. Framework preset: **Next.js** (default). Build command `npm run build`, output `.next`.
4. Add **Environment Variables** (Production and Preview as needed):
   - `NEXT_PUBLIC_SUPABASE_URL` — project URL from Supabase dashboard
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` — anon/public key from Supabase dashboard
5. **Do not** add `SUPABASE_DB_URL` to Vercel. It is for local/server seed scripts only and must never ship to browser code.
6. Apply migrations and run `make seed-supabase` locally (or from CI) against your hosted Supabase project before expecting live data on Vercel.
7. Without Supabase env vars on Vercel, the deployed app still works from committed sample JSON fixtures.

`/books/[id]` routes are generated on demand; the home page revalidates every 5 minutes (`revalidate = 300`).

## Local development workflow

Use **Cursor** connected to the WSL folder (`\\wsl$\Ubuntu\home\<user>\dev\booklens` or open `~/dev/booklens` from the WSL remote). Run all terminal commands inside WSL.

Good tool paths look like `/usr/bin/...`, `~/.nvm/...`, or `~/.local/bin/...`. Bad paths look like `/mnt/c/Program Files/...` or `/mnt/c/Users/...`.

## License

Portfolio / demo project. Add a license if you publish the repo publicly.
