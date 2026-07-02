# BookLens

BookLens is a portfolio-ready book discovery project focused on structured book metadata, better filtering, top tags, and explainable similar-book recommendations.

This repo currently contains:

- A Python data pipeline for collecting, cleaning, and prototyping recommendations.
- A minimal Next.js frontend foundation under `apps/web`.
- Project/deployment planning docs for WSL2, Cursor, Vercel, Supabase, Modal, and optional LiteLLM.

## Current scope

The smallest clean setup is intentional:

- Frontend: Next.js, deployed on Vercel.
- Backend: FastAPI on Modal only if a backend/API is needed later.
- Database/Auth/Storage: Supabase only when persistent app data, auth, or storage is needed.
- Optional LLM routing: LiteLLM only if model calls become part of the app.
- Local dev: Windows 11 host + WSL2 Ubuntu + Cursor.
- Secrets: never commit `.env` files, API keys, service-role keys, database URLs, or deployment credentials.

See [`docs/DESIGN.md`](docs/DESIGN.md) for the full design document and [`docs/PLAN.md`](docs/PLAN.md) for the shorter implementation plan.

## Repo structure

```text
booklens/
  apps/
    web/                         # Minimal Next.js frontend foundation
  data/
    fixtures/book_fixture.csv     # Offline demo input
    raw/.gitkeep                  # Generated raw API output goes here
    processed/.gitkeep            # Generated clean/report output goes here
  docs/
    DESIGN.md
    PLAN.md
    LOCAL_DEV_WSL_CURSOR.md
  scripts/                        # Python data pipeline steps
  run_pipeline.py                 # One-command data pipeline runner
  pyproject.toml                  # uv/Python project dependencies
  requirements.txt                # pip fallback dependencies
  Makefile                        # Common local commands
  .env.example                    # Placeholder environment variables only
```

## Local development recommendation

Use Cursor on Windows, but run the project inside WSL2 Ubuntu.

Good repo path:

```bash
~/dev/booklens
```

Avoid:

```bash
/mnt/c/Users/...
```

Open the repo in Cursor through the WSL integration and run commands in the WSL terminal.

Detailed setup: [`docs/LOCAL_DEV_WSL_CURSOR.md`](docs/LOCAL_DEV_WSL_CURSOR.md)

## Verify local tooling

From the repo root:

```bash
make check-env
```

Good paths should look like:

- `~/.nvm/...`
- `/usr/bin/...`
- `~/.local/bin/...`

Bad paths look like:

- `/mnt/c/Program Files/...`
- `/mnt/c/Users/...`

## Data pipeline

Install Python dependencies with `uv`:

```bash
uv sync
```

Run the offline demo:

```bash
make pipeline-demo
```

Or directly:

```bash
uv run python run_pipeline.py --mode demo
```

Expected generated outputs:

```text
data/raw/openlibrary_books.csv
data/processed/books_clean.csv
data/processed/top_tags.csv
data/processed/data_quality_report.txt
data/processed/similar_books_sample.csv
```

Run a small live Open Library collection:

```bash
make pipeline-live CONTACT=you@example.com
```

Or directly:

```bash
uv run python run_pipeline.py --mode live --contact you@example.com --limit-per-subject 25
```

## Web app

Install dependencies:

```bash
make web-install
```

Start the dev server:

```bash
make web-dev
```

Build for deployment:

```bash
make web-build
```

The Next.js app is intentionally minimal right now. Build features only after the data pipeline produces a clean catalog and useful tag counts.

## Environment variables

Copy `.env.example` to `.env` locally when needed. Commit only `.env.example`.

Never commit:

- `.env` files
- API keys
- Supabase service-role keys
- database URLs
- Vercel credentials
- Modal credentials
- model provider keys

## Deployment direction

- Deploy the frontend to Vercel when the first useful UI exists.
- Use Supabase for auth, Postgres, and storage only when the app needs those capabilities.
- Add FastAPI and Modal only when the app needs a separate Python API or backend job service.
- Add LiteLLM only when the app needs LLM/model calls.
