# BookLens Project Plan

## Current Goal

Build BookLens as a polished Supabase-backed book discovery and recommendation app:

- A deterministic Python data pipeline
- A Supabase Postgres database as the app data layer
- A Next.js frontend that reads book, tag, recommendation, and analytics data from Supabase
- Explainable similar-book recommendations
- A deployment-ready Vercel + Supabase structure

This repo already has:

- WSL/Cursor setup docs
- A Python data pipeline
- Open Library collection support
- Sample JSON fixtures
- A Next.js explorer shell
- Client-side filtering
- Supabase migrations, seeding, live reads, detail pages, analytics, and deployment verification

The current MVP is Supabase-backed. Keep the existing static fixture as a local fallback and development safety net, but make Supabase the intended production data source. The next plan is live data ingestion from APIs; see `docs/LIVE_DATA_PLAN.md`.

## Non-Goals For This Pass

Supabase is now in scope. These remain out of scope unless a later plan explicitly adds them:

- FastAPI backend
- Modal deployment
- LiteLLM or model-provider integrations
- Supabase Auth
- Supabase Storage
- User accounts, saved lists, comments, reviews, or social features
- Client-side writes to production tables
- Exposing service-role keys, database URLs, or other server-only secrets to browser code

## Current Repo State

Important existing files:

- `docs/DESIGN.md`: product/design source of truth
- `docs/LOCAL_DEV_WSL_CURSOR.md`: local environment guidance
- `pyproject.toml`: Python dependencies include pandas, requests, scikit-learn, python-dotenv, and ruff
- `scripts/run_pipeline.py`: cleans data, computes recommendations, and exports processed CSV + sample JSON
- `scripts/collect_openlibrary.py`: Open Library collector that writes raw CSV data
- `apps/web`: Next.js + TypeScript app
- `apps/web/src/data/*.sample.json`: committed sample fixture
- `apps/web/src/lib/booklens-data.ts`: fixture data helpers and shared lookups
- `apps/web/src/lib/load-booklens-data.ts`: server-side Supabase loader with fixture fallback
- `apps/web/src/lib/filters.ts`: client-side filtering helpers
- `.gitignore`: excludes `.env`, `.venv`, `node_modules`, `.next`, and generated `data/raw` / `data/processed`

Known gap: the hosted database now needs a safe live-data import workflow beyond the small committed fixture. Use `docs/LIVE_DATA_PLAN.md` for the API seeding roadmap.

## Architecture Decision

Use a Supabase-backed MVP:

1. Python scripts collect and process book data.
2. The pipeline continues to write local processed CSV/JSON outputs for reproducibility.
3. A seed/import workflow loads clean book, tag, and recommendation data into Supabase Postgres.
4. The Next.js app reads public book discovery data from Supabase.
5. Similarity remains precomputed by Python and stored in Supabase.
6. The committed sample JSON remains as a local fallback for development and tests.

Do not add FastAPI yet. Next.js can read public data directly from Supabase using the anon key and read-only RLS policies. If later server-only queries or protected writes become necessary, revisit API/server actions then.

## Supabase Scope

Use Supabase for:

- Postgres tables
- SQL migrations checked into the repo
- Public read-only data access from the frontend
- Seed/import scripts for local and hosted Supabase projects

Do not use Supabase for this pass:

- Auth
- Storage
- Realtime
- Edge Functions
- User-generated content

## Data Policy

Generated data stays out of Git by default:

- Keep `data/raw/` ignored.
- Keep `data/processed/` ignored.
- Keep the small committed fixture under `apps/web/src/data/` as fallback data.

Supabase schema changes must be committed as SQL migrations. Do not rely on ad hoc dashboard-only schema edits as the source of truth.

Recommended committed Supabase files:

- `supabase/migrations/*.sql`
- `supabase/README.md`
- optional seed SQL or documented seed command

## Data Contract

The frontend should continue exposing this TypeScript shape even if Supabase uses snake_case columns:

```ts
export type Book = {
  id: string;
  title: string;
  author: string;
  description: string;
  tags: string[];
  publicationYear: number | null;
  decade: string | null;
  pageCount: number | null;
  ratingCount: number | null;
  averageRating: number | null;
  coverUrl: string | null;
  source: string;
  sourceId: string;
};
```

Recommendation records should use:

```ts
export type BookRecommendation = {
  bookId: string;
  similarBookId: string;
  score: number;
  reasons: string[];
};
```

Top tag records should use:

```ts
export type TopTag = {
  tag: string;
  bookCount: number;
};
```

Reason labels should stay short and user-facing:

- `Shared tag`
- `Similar description`
- `Same author`
- `Same publication era`
- `Similar length`
- `Similar rating profile`

## Recommended Supabase Schema

Use SQL migrations. Names can change if implementation discovers a better local convention, but keep the data model simple.

### `books`

- `id text primary key`
- `title text not null`
- `author text not null`
- `description text not null default ''`
- `publication_year integer`
- `decade text`
- `page_count integer`
- `rating_count integer`
- `average_rating numeric(4, 2)`
- `cover_url text`
- `source text not null`
- `source_id text not null`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

Suggested constraints:

- publication year is null or within a plausible range
- page count is null or positive
- average rating is null or between 0 and 5
- rating count is null or non-negative
- unique `(source, source_id)`

### `book_tags`

- `book_id text not null references books(id) on delete cascade`
- `tag text not null`
- primary key `(book_id, tag)`

Suggested index:

- `(tag)`

### `book_recommendations`

- `book_id text not null references books(id) on delete cascade`
- `similar_book_id text not null references books(id) on delete cascade`
- `score numeric(7, 4) not null`
- `reasons text[] not null default '{}'`
- primary key `(book_id, similar_book_id)`

Suggested constraints:

- `book_id <> similar_book_id`
- score is non-negative

### Views

Create read-friendly views for the frontend:

- `books_with_tags`: one row per book with `tags text[]`
- `top_tags`: tag counts sorted by popularity

Optional later:

- `recommendations_with_books`: joined recommendation rows for detail pages

### RLS

Enable row-level security on tables and add public read policies for anon users:

- public can `select` books
- public can `select` book_tags
- public can `select` book_recommendations

Do not add public insert/update/delete policies.

## Implementation Phases For Cursor Composer

Completed phases:

1. Tighten local docs and commands
2. Build the data pipeline
3. Replace the Next.js starter with the app shell
4. Build client-side explorer filters
5. Supabase foundation (migrations, seed, env docs)
6. Supabase reads with fixture fallback
7. Book detail pages (`/books/[id]`)
8. Analytics section
9. Polish, deployment, and verification

Next phases:

- Phase 10: real Open Library seed
- Phase 11: provider identity tables
- Phase 12: Google Books enrichment
- Phase 13: optional popularity signals
- Phase 14: repeatable refresh workflow

See `docs/LIVE_DATA_PLAN.md` for detailed tasks, guardrails, and the Phase 10 Cursor prompt.

### Phase 5: Supabase Foundation

Goal: add Supabase schema, environment wiring, and a seed/import path without changing the user experience yet.

Tasks:

1. Add Supabase project structure:
   - `supabase/migrations/`
   - `supabase/README.md`
2. Add SQL migration for:
   - `books`
   - `book_tags`
   - `book_recommendations`
   - `books_with_tags` view
   - `top_tags` view
   - read-only RLS policies
3. Add or update environment docs:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - server-only `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_DB_URL` only for import scripts
4. Add Supabase client dependency to `apps/web` only if the frontend begins using Supabase in this phase. Otherwise defer dependency install to Phase 6.
5. Add a seed/import script that can load pipeline output into Supabase:
   - either from `apps/web/src/data/*.sample.json`
   - or from `data/processed/*.csv`
6. The seed/import script must not require or expose secrets in browser code.
7. Keep the current frontend reading static fixtures until Phase 6.

Acceptance criteria:

- SQL migration is committed and reviewable.
- Schema matches the frontend data contract.
- RLS permits anonymous reads only.
- Import/seed command is documented.
- No service-role key or database URL is exposed to `NEXT_PUBLIC_*` variables.
- Existing `npm run lint`, `npm run build`, and `make pipeline-demo` still pass.

### Phase 6: Frontend Supabase Reads

Goal: migrate the Next.js app from static JSON imports to Supabase reads while keeping fixture fallback available.

Tasks:

1. Install `@supabase/supabase-js` in `apps/web`.
2. Add a small Supabase browser/client helper.
3. Replace or extend `apps/web/src/lib/data.ts` so it can fetch:
   - books with tags
   - top tags
   - recommendations for a book
4. Map Supabase snake_case rows into existing TypeScript types.
5. Keep sample JSON fallback for local development when Supabase env vars are absent.
6. Add loading, error, and empty states where needed.
7. Preserve Phase 4 filter behavior.

Acceptance criteria:

- App works against Supabase when env vars are configured.
- App still works with sample fixtures when Supabase env vars are absent.
- Browser only uses `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- `npm run lint` and `npm run build` pass.

### Phase 7: Book Detail And Recommendations

Goal: make every book openable in a real detail experience backed by Supabase data.

Tasks:

1. Add a dynamic route:
   - `apps/web/src/app/books/[id]/page.tsx`
2. Render detail data from Supabase with fixture fallback.
3. Show:
   - cover when available
   - title
   - author
   - description
   - tags
   - publication year
   - page count
   - rating count
   - average rating
   - source/source id in a restrained metadata area
4. Show up to 5 similar books with reason chips.
5. Link explorer cards to detail pages while preserving a good in-page preview experience if desired.

Acceptance criteria:

- Every book can be opened.
- Unknown ids render `notFound()`.
- Similar books never include the selected book itself.
- Recommendation cards still look good with 1-2 reason chips and with 4-5 reason chips.
- `npm run lint` and `npm run build` pass.

### Phase 8: Supabase-Backed Analytics

Goal: add useful analytics from Supabase data without overbuilding.

Tasks:

1. Add analytics using Supabase data:
   - top tags
   - average rating by tag when enough rating data exists
   - publication year or decade distribution
   - page count vs average rating
   - rating count vs average rating
2. Keep charts simple. Use CSS/SVG or add a small chart dependency only if it clearly improves implementation.
3. Show unavailable-data states when Open Library fields are sparse.

Acceptance criteria:

- Analytics render from Supabase data.
- Fixture fallback still works.
- Sparse data does not produce misleading charts.
- Charts support the portfolio story rather than overwhelming the explorer.

### Phase 9: Polish, Deployment, And Verification

Goal: make the Supabase-backed MVP feel intentionally built and deployable.

Tasks:

1. Review spacing, typography, colors, responsive behavior, and empty states.
2. Verify the app with fixture fallback and Supabase env vars.
3. Document Vercel environment variables.
4. Document Supabase migration and seed workflow.
5. Run validation commands:
   - `make pipeline-demo`
   - `uv run ruff check scripts/`
   - `cd apps/web && npm run lint`
   - `cd apps/web && npm run build`
   - or `make verify` from the repo root

Acceptance criteria:

- All validation commands pass.
- Supabase migrations and seed/import workflow are documented.
- App can deploy to Vercel using Supabase anon env vars.
- No secrets or large generated datasets are committed.

## Cursor Composer Guardrails

When implementing:

- Prefer small, coherent commits or change sets.
- Follow the existing repo layout.
- Use SQL migrations for schema changes.
- Keep service-role keys and database URLs server-only.
- Do not create a FastAPI backend yet.
- Do not add Modal yet.
- Do not add LiteLLM yet.
- Do not add Supabase Auth or Storage yet.
- Do not commit `.env` or generated `data/raw` / `data/processed` files.
- Do not remove `.gitignore` protections for generated data.
- Do not depend on Windows paths or Windows-installed Node/Python.
- If adding frontend dependencies, keep them minimal and explain why.
- If Open Library data is sparse, make the UI honest about missing fields instead of fabricating ratings or page counts.

## Cursor Composer Prompts

Use one phase per Composer session. Keep the prompt narrow, then use the handoff template below so another reviewer can check the result before moving on.

### Phase 5 Prompt

```text
Read docs/DESIGN.md and docs/PLAN.md. Implement Phase 5 only: Supabase Foundation.

Important:
- Ignore booklens_repo_v4/. Do not read from it or copy code from it.
- Stay within Phase 5. Do not migrate the frontend to Supabase reads yet unless docs/PLAN.md explicitly says to.
- Do not add FastAPI, Modal, LiteLLM, Supabase Auth, Supabase Storage, user accounts, or backend services.
- Do not expose service-role keys or database URLs to browser code.
- Do not remove fixture JSON fallback files.

Before editing, inspect:
- docs/PLAN.md
- docs/DESIGN.md
- .env.example
- scripts/run_pipeline.py
- apps/web/src/data/books.sample.json
- apps/web/src/data/top-tags.sample.json
- apps/web/src/data/recommendations.sample.json
- apps/web/package.json

Goal:
Add the Supabase foundation: committed SQL migrations, clear env docs, and a safe seed/import workflow. Keep the current frontend behavior unchanged.

Implement:
1. Add `supabase/migrations/` with an initial SQL migration for:
   - `books`
   - `book_tags`
   - `book_recommendations`
   - `books_with_tags` view
   - `top_tags` view
   - read-only RLS policies for anon users
2. Add `supabase/README.md` documenting:
   - required local/hosted Supabase setup
   - migration workflow
   - seed/import workflow
   - which env vars are public vs server-only
3. Update `.env.example` if needed, using placeholders only.
4. Add a seed/import script if feasible in this phase:
   - read from existing sample JSON or processed CSVs
   - upsert books, tags, and recommendations
   - require server-only env vars only
   - do not run automatically in the browser
5. Update README or local docs only if command references change.

Validation:
- Run or explain `make pipeline-demo`.
- Run `uv run ruff check .` if Python scripts are changed.
- Run `cd apps/web && npm run lint` and `cd apps/web && npm run build` if frontend files are changed.

Output:
Provide a Phase Handoff using the template in docs/PLAN.md.
Include changed files, commands run, pass/fail results, important decisions, gaps/risks, and the recommended next phase.
```

### Phase Handoff Template

Use this after every Composer phase so the next reviewer can check the work quickly.

```markdown
## Phase Handoff

### Phase

Phase number and name:

### Summary

Briefly describe what changed and why.

### Files Changed

- `path/to/file`: short description of the change

### Commands Run

- `command`: pass/fail/not run, with a short note

### Acceptance Criteria Check

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

### Scope Check

- [ ] Stayed within the requested phase
- [ ] Did not add FastAPI, Modal, LiteLLM, Supabase Auth, or Supabase Storage
- [ ] Did not expose service-role keys, database URLs, or other secrets to browser code
- [ ] Did not commit secrets or generated large data
- [ ] Did not remove `.gitignore` protections

### Important Decisions

List any implementation or documentation choices that a reviewer should know about.

### Gaps Or Risks

List anything incomplete, uncertain, skipped, or needing review.

### Next Recommended Phase

State the next phase to implement and why.
```

## Useful Commands

From the repo root:

```bash
make check-env
uv sync
make pipeline-demo
uv run ruff check .
```

From `apps/web`:

```bash
npm install
npm run dev
npm run lint
npm run build
```

Optional live collection command:

```bash
uv run python scripts/collect_openlibrary.py --contact you@example.com --limit-per-subject 25
```

After live collection, rerun the pipeline command for Open Library input and seed Supabase from the processed output.

## Definition Of Done

The Supabase-backed MVP pass is done when:

- The Python pipeline produces clean processed data.
- Supabase migrations define the durable data model.
- A documented seed/import workflow loads books, tags, and recommendations.
- The web app can read from Supabase with fixture fallback.
- Search, filters, top tags, detail view, recommendations, reason chips, and analytics all work.
- The app builds successfully.
- Documentation explains how to reproduce the workflow from WSL/Cursor.
- The repo remains small, understandable, and free of secrets.
