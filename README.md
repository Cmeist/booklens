# BookLens

BookLens is an interactive book discovery and recommendation web app built as a data analytics portfolio project. Users explore books with useful filters, browse popular tags, and see explainable similar-book recommendations.

## Current MVP direction

This repo is building a **static-data MVP**:

1. Python scripts collect and process book data.
2. The pipeline writes processed CSVs locally and (in later phases) a small JSON fixture for the web app.
3. The Next.js app reads that fixture and renders the explorer, detail views, and analytics.
4. Similarity and recommendation reasons are precomputed in Python.

**Not in scope yet:** FastAPI, Modal, Supabase, auth, LiteLLM, or user accounts. Those are documented in `docs/DESIGN.md` as future options only.

See `docs/PLAN.md` for the phased build plan and `docs/DESIGN.md` for product and design goals.

## Repo structure

```text
booklens/
├── apps/web/              # Next.js + TypeScript frontend
├── data/
│   ├── raw/               # Generated raw CSVs (Git-ignored)
│   └── processed/         # Generated processed CSVs (Git-ignored)
├── docs/
│   ├── DESIGN.md          # Product and design source of truth
│   ├── PLAN.md            # Implementation phases for Cursor
│   └── LOCAL_DEV_WSL_CURSOR.md
├── scripts/
│   ├── run_pipeline.py    # Demo pipeline (writes sample processed data)
│   └── collect_openlibrary.py
├── .env.example           # Safe to commit (placeholders only)
├── Makefile               # Common local commands
├── pyproject.toml         # Python project (uv)
└── uv.lock
```

Generated outputs under `data/raw/` and `data/processed/` stay out of Git. Only a small curated web fixture under `apps/web/src/data/` will be committed for the deployed demo (Phase 2+).

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

## Common commands

From the repo root:

| Command | Purpose |
| --- | --- |
| `make check-env` | Print paths for git, node, npm, python3, and uv |
| `make pipeline-demo` | Run the demo data pipeline |
| `make web-dev` | Start the Next.js dev server |
| `make web-build` | Production build of the web app |
| `make status` | Show `git status` |
| `uv run ruff check .` | Lint Python code |

From `apps/web`:

| Command | Purpose |
| --- | --- |
| `npm run dev` | Dev server (same as `make web-dev`) |
| `npm run build` | Production build (same as `make web-build`) |
| `npm run lint` | ESLint |
| `npm run start` | Serve a production build |

Optional live data collection (network required; not needed for the demo pipeline):

```bash
uv run python scripts/collect_openlibrary.py --contact you@example.com --limit-per-subject 25
```

## Environment and secrets

- Copy `.env.example` to `.env` for local-only values. **Never commit `.env`.**
- `.env.example` uses placeholders only and is safe to commit.
- Do not commit API keys, database URLs, service-role keys, or other secrets.
- Most MVP work does not require a populated `.env` yet.

## Local development workflow

Use **Cursor** connected to the WSL folder (`\\wsl$\Ubuntu\home\<user>\dev\booklens` or open `~/dev/booklens` from the WSL remote). Run all terminal commands inside WSL.

Good tool paths look like `/usr/bin/...`, `~/.nvm/...`, or `~/.local/bin/...`. Bad paths look like `/mnt/c/Program Files/...` or `/mnt/c/Users/...`.

## License

Portfolio / demo project. Add a license if you publish the repo publicly.
