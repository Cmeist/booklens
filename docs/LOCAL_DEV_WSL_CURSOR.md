# Local Development: Windows 11 + WSL2 + Cursor

This guide is the complete setup checklist for BookLens. All commands assume a **WSL2 Ubuntu** terminal unless noted otherwise.

## Why WSL-first

BookLens is developed on a Windows 11 host, but the **runtime is WSL2 Ubuntu**:

- Faster file I/O than working directly under `/mnt/c/...`
- Linux-native Node, Python, uv, git, and make
- Same environment as typical deployment tooling
- Cursor integrates cleanly with the WSL filesystem

Do **not** run `npm install`, `uv sync`, or project scripts from Windows PowerShell against a repo under `/mnt/c/...`.

## 1. Clone or open the repo on a Linux path

Recommended location:

```bash
mkdir -p ~/dev
cd ~/dev
git clone <your-repo-url> booklens
cd booklens
```

Your prompt should show a path like `/home/<user>/dev/booklens`, **not** `/mnt/c/Users/...`.

If you already cloned under Windows, move or re-clone into WSL instead of developing from `/mnt/c/...`.

## 2. Open the project in Cursor

1. Install Cursor on Windows.
2. Use **File → Open Folder** and choose the WSL path, for example `\\wsl$\Ubuntu\home\<user>\dev\booklens`, or open `~/dev/booklens` when connected to WSL.
3. Open the integrated terminal and confirm the shell is WSL (Ubuntu), not PowerShell or cmd.

All Makefile and npm commands in this doc run from the **repo root** unless a step says otherwise.

## 3. Install required tools (one-time)

Install these **inside WSL**:

| Tool | Minimum | Notes |
| --- | --- | --- |
| Git | any recent | `sudo apt update && sudo apt install -y git` |
| Python | 3.12+ | `python3 --version` |
| uv | latest | [uv install docs](https://docs.astral.sh/uv/getting-started/installation/) |
| Node.js | 20+ recommended | Prefer [nvm](https://github.com/nvm-sh/nvm) inside WSL |
| npm | bundled with Node | Comes with Node |
| make | any | `sudo apt install -y make` if missing |

Example nvm install (adjust version as needed):

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
```

## 4. Confirm tool paths

From the repo root:

```bash
make check-env
```

Expected: every path is under WSL Linux locations such as `/usr/bin/...`, `~/.nvm/...`, or `~/.local/bin/...`.

**Red flags** (fix before continuing):

- `/mnt/c/Program Files/...`
- `/mnt/c/Users/...`
- Windows AppData or `cmd.exe`-style paths

If Node or npm are missing, install them in WSL (step 3) and re-run `make check-env`. The Makefile tolerates missing node/npm with `|| true`, but frontend work requires both.

## 5. Python setup

From the repo root:

```bash
uv sync
```

This creates `.venv/` (Git-ignored) and installs dependencies from `pyproject.toml`, including pandas, requests, scikit-learn, and python-dotenv. Dev tools such as ruff are installed via the dev dependency group.

Verify:

```bash
uv run python --version
uv run ruff check .
```

## 6. Frontend setup

From the repo root:

```bash
cd apps/web
npm install
cd ../..
```

This installs Next.js, React, TypeScript, Tailwind, and ESLint into `apps/web/node_modules/` (Git-ignored).

The web app lives in `apps/web/`. Use npm scripts there, or the Makefile shortcuts from the repo root (steps 7–8).

## 7. Run the demo pipeline

From the repo root:

```bash
make pipeline-demo
```

This runs `uv run python scripts/run_pipeline.py` with built-in demo data. **No network access is required.**

Expected outputs (local only, Git-ignored):

- `data/raw/demo_books.csv`
- `data/processed/books_clean.csv`
- `data/processed/top_tags.csv`
- `data/processed/data_quality_report.txt`

These directories are excluded by `.gitignore`. Do not commit generated CSVs.

## 8. Run the web app

**Development server** (from repo root):

```bash
make web-dev
```

Equivalent: `cd apps/web && npm run dev`. Opens [http://localhost:3000](http://localhost:3000).

**Production build** (from repo root):

```bash
make web-build
```

Equivalent: `cd apps/web && npm run build`.

Other useful frontend commands from `apps/web`:

```bash
npm run lint
npm run start   # after a successful build
```

## 9. Environment variables and secrets

- **`.env`** — local only. Copy from `.env.example` when you need env vars. Never commit `.env`.
- **`.env.example`** — placeholder names only. Safe to commit.
- **Real secrets** — API keys, Supabase service-role keys, database URLs, deployment credentials, and model provider keys must never be committed.

The current static-data MVP does not require a filled `.env` for demo pipeline or local frontend work. Placeholders in `.env.example` reference future Supabase/API integration documented in `docs/DESIGN.md`; those services are **not** part of the current MVP pass.

## 10. Generated data policy

Git ignores:

- `data/raw/` — raw collection output
- `data/processed/` — cleaned CSVs and reports from the pipeline

Later phases will commit a **small** JSON fixture under `apps/web/src/data/` for the deployed demo. Until then, treat all pipeline output as disposable local files.

Optional live collection (network required; separate from the demo pipeline):

```bash
uv run python scripts/collect_openlibrary.py --contact you@example.com --limit-per-subject 25
```

The collector writes to `data/raw/`. Processing that live data into web-ready fixtures is planned for Phase 2 (`docs/PLAN.md`).

## 11. What is out of scope for this MVP pass

Do not expect these in the current repo setup:

- **FastAPI** backend
- **Modal** deployment
- **Supabase** database, auth, or storage
- **LiteLLM** or other model-provider routing
- User accounts, saved lists, or social features

They may appear in design docs as future options. The MVP is a Python pipeline plus a static-data Next.js app on Vercel.

## 12. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Slow installs or file watchers | Repo under `/mnt/c/...` | Move repo to `~/dev/booklens` |
| `make check-env` shows `/mnt/c/...` | Windows Node/Python on PATH | Install tools in WSL; open Cursor on WSL folder |
| `uv: command not found` | uv not installed in WSL | Install uv; ensure `~/.local/bin` is on PATH |
| `npm: command not found` | Node not installed in WSL | Install Node via nvm inside WSL |
| Pipeline writes files but Git is clean | Expected | `data/raw/` and `data/processed/` are ignored |
| Accidentally created `.env` with secrets | Risk of commit | Keep `.env` local; never `git add .env` |

## 13. Daily workflow checklist

Use this after a fresh clone or when onboarding:

- [ ] Repo path is `~/dev/booklens` (or similar Linux path), not `/mnt/c/...`
- [ ] Cursor terminal is WSL Ubuntu
- [ ] `make check-env` shows Linux tool paths
- [ ] `uv sync` completed successfully
- [ ] `cd apps/web && npm install` completed successfully
- [ ] `make pipeline-demo` wrote files under `data/raw/` and `data/processed/`
- [ ] `make web-dev` serves the app at [http://localhost:3000](http://localhost:3000)
- [ ] No `.env` or generated data files staged for commit

## Reference: Makefile shortcuts

From repo root:

```bash
make check-env      # verify tool paths
make pipeline-demo  # run demo Python pipeline
make web-dev        # Next.js dev server
make web-build      # Next.js production build
make status         # git status
```

See also `README.md` and `docs/PLAN.md` for phase-by-phase implementation goals.
