# BookLens Supabase

This folder contains the committed Postgres schema for BookLens. Supabase is the production data layer; the Next.js app reads public book data with the anon key when `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set.

If those vars are absent (for example on a fresh Vercel deploy without configuration), the frontend falls back to committed JSON under `apps/web/src/data/*.sample.json`.

## What is included

- `migrations/20260302000000_initial_booklens_schema.sql`
  - `books`
  - `book_tags`
  - `book_recommendations`
  - `books_with_tags` view
  - `top_tags` view
  - read-only RLS policies for the `anon` role
- `migrations/20260703150000_provider_identity_tables.sql`
  - `book_sources` — maps canonical `book_id` to provider IDs (server-only RLS)
  - `book_isbns` — normalized ISBNs for cross-provider matching (server-only RLS)
  - `ingestion_runs` — audit log for seed/import attempts (server-only RLS)
- `migrations/20260713160000_book_popularity_signals.sql`
  - `book_popularity_signals` — optional bestseller/list context (server-only RLS)
  - Does not alter core `books` columns
  - No anon select policies (frontend stays usable without this table)

## Prerequisites

You need either:

- a hosted Supabase project, or
- the [Supabase CLI](https://supabase.com/docs/guides/cli) for local development

Install the CLI if you want local migrations:

```bash
npm install -g supabase
```

## Environment variables

Copy `.env.example` to `.env` locally. Never commit `.env`.

### Frontend-safe (browser / Vercel)

Set these on Vercel and in local `.env` when you want live reads:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Do **not** set `SUPABASE_DB_URL` on Vercel. Seed and import scripts use it locally or in server-only automation only.

### Server-only (seed/import scripts only)

These must never be prefixed with `NEXT_PUBLIC_` and must never ship to browser code:

- `SUPABASE_DB_URL` — Postgres connection string used by `scripts/seed_supabase.py` and `scripts/import_popularity_signals.py --write-db`
- `SUPABASE_SERVICE_ROLE_KEY` — optional for future server-only tooling
- `SUPABASE_URL` — optional server-side project URL
- `SUPABASE_ANON_KEY` — optional server-side anon key copy
- `GOOGLE_BOOKS_API_KEY` — optional Google Books enrichment
- `NYT_BOOKS_API_KEY` — optional NYT Books API popularity import (non-commercial; ~500/day, 5/min)

For Phase 5 seeding, set `SUPABASE_DB_URL` only.

Example source for the DB URL in the Supabase dashboard:

`Project Settings → Database → Connection string → URI`

From **WSL**, prefer the **Session pooler** URI (`postgres.<project-ref>@...pooler.supabase.com:5432`). The direct `db.<project-ref>.supabase.co` host often resolves to IPv6 and fails from WSL.

From Linux/macOS hosts with working direct Postgres access, the direct URI is fine.

## Migration workflow

### Hosted Supabase

1. Create a Supabase project.
2. Open the SQL editor or link the repo with the Supabase CLI.
3. Apply the migration file in order:

```bash
supabase login
supabase link --project-ref <your-project-ref>
supabase db push
```

If you are not using the CLI, paste the contents of each file in `migrations/` into the Supabase SQL editor and run them in filename order.

### Local Supabase

```bash
supabase start
supabase db reset
```

`db reset` applies committed migrations to the local database.

## Seed/import workflow

The frontend reads Supabase when public env vars are configured. Seeding is required for live production data; without it, the app uses fixtures.

### 1. Run the pipeline (optional for CSV source)

```bash
make pipeline-demo
```

### 2. Apply migrations

Use the migration workflow above.

### 3. Set server-only env vars

In `.env`:

```bash
SUPABASE_DB_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

### 4. Seed from sample JSON (default)

```bash
uv sync
make seed-supabase
```

Equivalent:

```bash
uv run python scripts/seed_supabase.py
```

### 5. Seed from processed CSV instead

```bash
uv run python scripts/seed_supabase.py --source csv
```

This reads:

- `data/processed/books_clean.csv`
- `data/processed/recommendations.csv`

### 6. Seed from live Open Library data

```bash
make collect-openlibrary
make pipeline-openlibrary
make enrich-google-books
make seed-supabase SOURCE=csv
```

`seed_supabase.py` prefers `data/processed/books_enriched.csv` when it exists and is newer than `books_clean.csv`.

### 7. Google Books enrichment

Requires `GOOGLE_BOOKS_API_KEY` in repo-root `.env` (server-only).

```bash
make enrich-google-books
make enrich-google-books LIMIT=3   # smoke test on first 3 rows
```

`LIMIT=N` limits API calls only; the output CSV still includes all input rows.

Reads `data/processed/books_clean.csv`, writes:

- `data/processed/books_enriched.csv`
- `data/processed/google_books_enrichment_report.txt`

Enriched CSV columns consumed by seeding:

- `isbns` — JSON array, e.g. `[{"isbn":"978...","isbnType":"ISBN_13","provider":"googlebooks"}]`
- `extra_sources` — JSON array with Google Books `provider` / `provider_id` for `book_sources`

Primary `books.source` and `books.source_id` remain the Open Library values.

See `docs/LIVE_DATA_PLAN.md` for the full live-data workflow and quality report details.

## Popularity signals (NYT Books API)

Phase 13 stores optional bestseller/list context in `book_popularity_signals`. It never writes to core `books` columns (`title`, `author`, `description`, `page_count`, `average_rating`, `rating_count`).

### Provider choice

- **Source:** New York Times Books API bestseller lists only
- **Terms:** non-commercial Developer Portal use; attribution required
- **Quota:** typically 500 requests/day and 5 requests/minute (sleep ~12s between list calls)
- **Key:** `NYT_BOOKS_API_KEY` in repo-root `.env` (server-only, never `NEXT_PUBLIC_`)

### Workflow

1. Apply migrations (includes `20260713160000_book_popularity_signals.sql`).
2. Ensure a catalog CSV exists (`data/processed/books_enriched.csv` preferred, else `books_clean.csv`).
3. Smoke match/report (no DB write):

```bash
# Offline fixture smoke (no live API)
make import-popularity-signals LIMIT=3 FROM_JSON=scripts/fixtures/nyt_hardcover_fiction_sample.json

# Live API smoke (requires NYT_BOOKS_API_KEY)
make import-popularity-signals LIMIT=3
```

4. Review:

- `data/processed/popularity_signals_report.json`
- `data/processed/popularity_signals_report.txt`

5. Hosted DB write only after explicit approval (asks before large harvests / hosted deletes):

```bash
make import-popularity-signals LIMIT=3 WRITE_DB=1
```

Matching rules (auto-import strong/medium only):

| Strength | Rule | Imported? |
| --- | --- | --- |
| strong | shared ISBN | yes |
| medium | normalized title + first author | yes |
| weak | title-only | report only |

### Verify after import

```sql
select count(*) from public.book_popularity_signals;
select provider, list_name, count(*)
from public.book_popularity_signals
group by provider, list_name
order by count(*) desc;
```

| Table | Purpose | Anon access |
| --- | --- | --- |
| `book_popularity_signals` | NYT (or future) list/rank signals linked to `books.id` | None |

## Provenance tables

Phase 11 adds server-only provenance tables. The frontend still reads only `books`, tags, recommendations, and views.

| Table | Purpose | Anon access |
| --- | --- | --- |
| `book_sources` | Links each book to provider IDs (`openlibrary`, `demo`, etc.) | None |
| `book_isbns` | Normalized ISBNs for future cross-provider matching | None |
| `ingestion_runs` | Audit trail for each `seed_supabase.py` run | None |
| `book_popularity_signals` | Optional NYT list/rank signals | None |

`make seed-supabase` (JSON or CSV) upserts:

1. `books`, `book_tags`, `book_recommendations` (unchanged frontend contract)
2. `book_sources` from each row's `source` + `source_id`
3. An `ingestion_runs` record with insert/update/error counts

`book_isbns` stays empty until enrichment provides real ISBNs (Phase 12). The seed script does not fabricate ISBNs.

### Provider ID mapping

Canonical BookLens `books.id` is a stable hash. Provider identity lives in `book_sources`:

```text
books.id  ←→  book_sources (provider, provider_id)
```

Example Open Library row:

- `books.source` / `books.source_id` — primary provider fields used by the app today
- `book_sources.provider` = `openlibrary`
- `book_sources.provider_id` = `/works/OL123W` (work key from collection)
- `book_sources.provider_url` = `https://openlibrary.org/works/OL123W`

Verify provenance after seeding:

```sql
select count(*) from public.book_sources;
select provider, count(*) from public.book_sources group by provider;
select id, provider, mode, status, inserted_count, updated_count, finished_at
from public.ingestion_runs
order by started_at desc
limit 5;
```

## Security notes

- RLS allows anonymous `select` only.
- There are no public insert/update/delete policies.
- The seed script uses `SUPABASE_DB_URL` and runs only from the CLI.
- Do not put service-role keys or database URLs in `NEXT_PUBLIC_*` variables.
- Keep `apps/web/src/data/*.sample.json` as the local fixture fallback.

## Verify seeded data

After seeding, run simple checks in the Supabase SQL editor:

```sql
select count(*) from public.books;
select * from public.top_tags;
select * from public.books_with_tags limit 5;
```

`top_tags` is ordered by `book_count desc, tag asc` in the view definition.

## Vercel deployment

1. In Vercel project settings, set **Root Directory** to `apps/web`.
2. Add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` from the Supabase dashboard (Settings → API).
3. Do not add `SUPABASE_DB_URL` to Vercel.
4. Apply migrations and run `make seed-supabase` from a trusted machine with `SUPABASE_DB_URL` in `.env`.
5. Redeploy or wait for ISR revalidation (home page: 5 minutes) to pick up seeded data.

Without public Supabase vars, Vercel serves the committed sample fixture — useful for demos before the database is wired up.

## Fixture fallback

Keep `apps/web/src/data/*.sample.json` in the repo. The server loader uses them when:

- public Supabase env vars are unset, or
- a Supabase fetch fails (warning banner shown on the explorer/detail pages).
