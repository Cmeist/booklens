# BookLens Project Plan

This is the shorter implementation plan. See `DESIGN.md` for the full product, architecture, local development, deployment, and secrets design.

## Current recommendation

Start with the smallest clean setup:

1. Keep the existing Python data pipeline as the foundation for collection, cleaning, top tags, and recommendation prototyping.
2. Add a minimal Next.js frontend under `apps/web` so the project has a deployment-ready web surface.
3. Use Supabase only when the app needs persistent app data, auth, or storage.
4. Add FastAPI on Modal only when the frontend needs a real backend/API beyond static files or Supabase client queries.
5. Add LiteLLM only if the app actually needs model calls.

Do not add backend, auth, storage, or LLM infrastructure before there is a concrete product need.

## Product MVP

BookLens helps readers find better books faster using structured book metadata, top tags, and explainable similar-book recommendations.

### Core book fields

- Title
- Author
- Description
- Genre / subject tags
- Publication year
- Page count
- Rating count
- Average rating
- Cover URL, when available, for product polish

### Essential features

1. Advanced book explorer
2. Top 10 popular tags
3. Book detail pages
4. Similar-books recommendation prototype
5. Recommendation explanation chips
6. Small analytics view using tags, years, ratings, and page counts

### Lower priority

- Hidden gems section
- User accounts
- Saved lists
- Full collaborative filtering
- LLM-based summaries or recommendation explanations

## Technical plan

### Frontend

- Next.js
- Deployed on Vercel
- Located in `apps/web`
- Browser-safe environment variables must use `NEXT_PUBLIC_*`

Likely frontend env vars:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL`, if a separate backend/API is created

### Backend/API

- FastAPI
- Deployed on Modal, if a backend/API is needed
- Do not add this until the app needs server-side recommendation endpoints, scheduled enrichment jobs, protected database writes, or service-role Supabase access.

Local backend dev command should look like:

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Likely backend env vars:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL`
- `MY_APP_API_KEY` or another service-to-service secret
- Optional provider keys such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.

### Database/Auth/Storage

- Supabase
- Use Supabase Auth for users if needed.
- Use Supabase Postgres as the source of truth for app data if/when the app needs persistent data.
- Use Supabase Storage for uploads/assets if needed.
- Use migrations for schema changes.
- Do not rely on ORM auto-generated production schema as the source of truth.

Frontend-safe Supabase env vars:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Server-only Supabase env vars:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL`
- Any JWT/auth secret needed by the backend

Rules:

- Service-role keys must never be exposed to the browser.
- Database URLs must be server-only.
- Put real values in local `.env` files and deployment dashboards only.
- Commit only `.env.example` with placeholder names.

### Optional LLM routing

- LiteLLM only if this app needs model calls.
- Do not add LiteLLM for the first static/metadata/recommendation MVP.
- If added later, keep provider keys server-side only.

### Local development

- Windows 11 host
- WSL2 Ubuntu runtime
- Cursor editor using the WSL integration
- Linux-side tooling only: Node, npm/pnpm, Python, uv, git, make

## Windows 11 + WSL2 + Cursor rules

Work inside WSL2 Ubuntu, not directly under `/mnt/c/...`.

Recommended repo path:

```bash
~/dev/booklens
```

Open the WSL folder from Cursor using the WSL integration. Run terminal commands inside WSL.

Do not run `npm install` from Windows tooling inside the WSL repo. Avoid Windows Node/npm/Python bleeding into the WSL PATH.

Confirm these resolve to Linux paths:

```bash
which node
which npm
which python
which uv
which git
```

Good paths look like:

- `~/.nvm/...`
- `/usr/bin/...`
- `~/.local/bin/...`

Bad paths look like:

- `/mnt/c/Program Files/...`
- `/mnt/c/Users/...`

If package binaries break, for example `node_modules/.bin/next` becomes a regular file instead of a symlink/executable, assume Windows npm polluted the install. Delete `node_modules` and reinstall from a clean WSL terminal using Linux npm.

## WSL setup checklist

Inside WSL2 Ubuntu:

```bash
sudo apt update
sudo apt install -y git make curl build-essential
```

Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Node 20+ via `nvm`:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
```

Create a dev folder:

```bash
mkdir -p ~/dev
cd ~/dev
```

Clone/open the repo there.

## Secrets policy

Never commit:

- `.env` files
- API keys
- Supabase service-role keys
- Supabase database URLs
- Vercel deployment credentials
- Modal deployment credentials
- Model provider keys

Commit only:

- `.env.example` files with placeholder names
- Documentation describing what variables are needed

## Deployment plan

### Vercel

If using Next.js, deploy the frontend to Vercel.

Configure Vercel environment variables in the Vercel dashboard. Use browser-safe `NEXT_PUBLIC_*` values only for public frontend config. Keep privileged secrets out of frontend code unless they are server-only environment variables used by Next.js server actions or route handlers.

Likely Vercel env vars:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL`, if there is a separate backend
- Any app-specific public config

### Modal

If using FastAPI or Python backend services, deploy the backend to Modal.

Store secrets in Modal Secrets, not committed files. Backend code should read configuration from environment variables.

Do not deploy until the developer explicitly confirms deployment is desired.

Likely Modal/backend env vars:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL`
- `MY_APP_API_KEY` or another service-to-service secret
- Optional provider keys such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.

## Immediate implementation sequence

1. Run the data pipeline demo in WSL.
2. Run a small live Open Library collection.
3. Inspect `books_clean.csv`, `top_tags.csv`, and `data_quality_report.txt`.
4. Build the first Explore page using a small static export or local JSON generated from the cleaned CSV.
5. Add Supabase only when persistent data is needed.
6. Add FastAPI/Modal only when a separate API is needed.
7. Add LiteLLM only if LLM features become part of the app.
