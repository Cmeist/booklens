# BookLens Live Data Plan

This plan starts the next stage after the Supabase-backed MVP: importing real book data from APIs, enriching sparse records, and seeding Supabase safely.

The goal is not to make the frontend call third-party APIs. The Python pipeline should collect, normalize, enrich, score, and seed the database. The Next.js app should keep reading from Supabase with the existing fixture fallback.

## Current Baseline

Already available:

- Supabase schema for `books`, `book_tags`, `book_recommendations`, `books_with_tags`, and `top_tags`
- `scripts/collect_openlibrary.py` for Open Library subject collection
- `scripts/run_pipeline.py` for cleaning, recommendations, CSV export, and JSON fixtures
- `scripts/seed_supabase.py` for seeding Supabase from sample JSON or processed CSV
- `scripts/enrich_openlibrary_ratings.py` for Open Library work-level community ratings
- `scripts/enrich_openlibrary_pages.py` for edition-derived page count fills
- `scripts/enrich_google_books.py` for Google Books fill-missing metadata and ISBN/source enrichment
- `scripts/import_popularity_signals.py` for optional NYT bestseller/list signals (`book_popularity_signals`)
- `make pipeline-demo`
- `make seed-supabase`
- `make import-popularity-signals`
- `make verify`
- Next.js app reading Supabase with fixture fallback

Main limitation:

- The current schema tracks only one `source` and `source_id` per book. That is enough for a single Open Library seed, but it is too thin for multi-API enrichment.
- The current frontend loads the complete book set into the browser. That is fine for the MVP and portfolio-scale datasets, but million-book catalogs must use server-side pagination, search, filtering, and precomputed aggregates.
- User profile, logging, compatibility scoring, and tag UX are active frontend work areas. Live-data phases must not refactor those flows unless a phase explicitly says so.

## Composer Execution Notes

Use this document as a plan for data and deployment agents, not as permission to implement every future idea at once.

Before editing for any phase:

1. Run `git status --short` and identify unrelated dirty files. Preserve them.
2. Read the files named in that phase's scope before editing.
3. Confirm whether generated files under `data/raw/`, `data/processed/`, or `apps/web/src/data/*.sample.json` are dirty. Do not commit generated live data unless the project owner explicitly asks.
4. Keep secrets in `.env`, `.env.local`, Supabase secrets, or Modal secrets only. Never print secret values in handoff.
5. If a phase needs live API calls, run the smallest smoke test first (`LIMIT=3` or `LIMIT_TOTAL=5`) and report exact row counts.
6. If a phase needs hosted Supabase writes, use `SUPABASE_DB_URL` from local/server-only environment only. Never add it to Vercel.

Stop and ask before:

- adding a new paid API provider
- changing the canonical `books` table shape in a way that requires frontend rewrites
- deleting or replacing hosted Supabase data
- committing generated data files
- running large API harvests beyond the phase's requested limits
- adding auth, user tables, FastAPI, LiteLLM, or browser-side provider API calls

## Scale Direction

BookLens should be designed so the same conceptual structure can grow from a small portfolio dataset to millions of books.

The current implementation is a deliberately small batch MVP:

- Python collects and enriches data offline.
- Supabase stores canonical books, tags, recommendations, and provenance.
- The frontend reads public data from Supabase with fixture fallback.
- Recommendations and analytics are precomputed or derived from loaded rows.

That shape can scale, but not by loading every book into the browser or recomputing similarity at request time. At large scale, keep the same boundaries and evolve the internals:

- Ingestion remains batch-oriented and resumable.
- Provider records remain traceable through `book_sources`, `book_isbns`, and ingestion audit tables.
- The app reads from indexed read models, not raw provider payloads.
- Search, filtering, recommendations, and analytics are served from precomputed tables or search indexes.
- Browser responses are paginated and bounded.

### Million-Book Read Path

For millions of books, the frontend should not query `select * from books_with_tags`.

Target read pattern:

1. Server-side search endpoint, Supabase RPC, or Postgres view accepts search/filter/sort/page parameters.
2. Query uses indexes and returns one page of compact book cards.
3. Detail pages fetch one book plus a small recommendation set.
4. Analytics pages read precomputed aggregate tables, not all books.
5. The browser never needs the whole catalog in memory.

Recommended future indexes/read models:

- `books(title)` or full-text `tsvector` index for title/author/description search
- `book_tags(tag, book_id)` for tag filters
- `books(publication_year)`, `books(page_count)`, and `books(average_rating)` for range filters
- `book_recommendations(book_id, score desc)` for detail recommendations
- materialized or maintained tables for `top_tags`, decade counts, rating distributions, and other analytics

### Million-Book Write Path

For large imports, do not upsert one row at a time forever.

Target ingestion pattern:

1. Collect raw provider pages into provider-specific raw files or object storage.
2. Normalize into staging tables or chunked CSV/Parquet files.
3. Match and merge in batches using ISBN/provider IDs first.
4. Bulk load into staging tables.
5. Upsert canonical tables in transactions per chunk.
6. Record every batch in `ingestion_runs`.
7. Refresh recommendation and analytics read models after successful batches.

Recommended future tables:

- `provider_raw_records` or external raw storage manifests for raw payload provenance
- `book_search_documents` for search-ready text and denormalized fields
- `book_similarity_jobs` for offline recommendation computation status
- `book_analytics_snapshots` for precomputed dashboard aggregates

### Recommendation Scale

The current TF-IDF similarity approach is fine for hundreds or low thousands of books. For millions of books:

- compute recommendations offline in batches
- store only top N recommendations per book
- avoid full pairwise similarity across the whole catalog
- use candidate generation first, such as shared tags, author, publication era, ISBN/work clusters, or vector/search index candidates
- keep reason chips generated and stored with each recommendation

The product contract stays the same: detail pages show a small, explainable set of similar books. The computation strategy changes behind the scenes.

## Source Priority

Use sources in this order.

### 1. Open Library

Role: primary discovery source **and primary ratings source**.

Use for:

- Work/title discovery by subject
- Author names
- Descriptions when available
- Subjects/tags
- First publication year
- Cover IDs and cover URLs
- Open Library work IDs
- Community star ratings (`ratings_average`, `ratings_count`) via Search API or `/works/{id}/ratings.json`

Notes:

- Keep requests identified with `User-Agent` and contact email.
- Keep rate limits conservative.
- Cache raw responses locally under `data/raw/`.
- Do not use Open Library as a high-volume production backend.
- Ratings attach to **works**, not editions. Match on existing `source_id` (`/works/OL…W`).

### 2. Google Books

Role: optional metadata enrichment; **secondary** ratings source.

Use for:

- Page counts
- Published dates
- Descriptions when Open Library is blank
- Category hints
- Image links
- ISBNs and industry identifiers
- `volumeInfo.averageRating` / `ratingsCount` when present

Notes:

- Use a server-only API key from `.env`.
- Do not expose the key to Next.js.
- Treat Google Books volume IDs as provider IDs, not canonical app IDs.
- Match by ISBN first, then normalized title plus author.
- Google ratings coverage is thin on ISBN-matched classics; do not rely on it as the primary fill.

### 3. New York Times Books API Or Similar Bestseller Sources

Role: optional popularity signal, not canonical metadata.

Use for:

- Bestseller/list membership
- Current or historical popularity labels
- Discovery seed lists for later enrichment

Notes:

- Use only if the API terms and quota are acceptable.
- Store list/rank information separately from core book metadata.
- Do not overwrite bibliographic fields just because a popularity source has a partial title.

### Ratings API survey (2026-07)

Spike on the live ~1.1k catalog (sample n=50 each):

| Source | Match key | Ratings hit rate | Notes |
|--------|-----------|------------------|-------|
| Open Library Search `ratings_*` | work id | **80%** (40/50 with `ratings_count > 0`) | Best primary source |
| Google Books Volumes | ISBN from enriched CSV | **4%** overall (2/50); 20% of volume matches | Weak; keep as upgrade only |
| Hardcover GraphQL | ISBN / title | Not spiked | Optional Phase 2 if OL gaps remain |
| Goodreads | — | N/A | Public API shut down; do not scrape |
| NYT Books | ISBN / lists | N/A for stars | Bestseller / critic signal only |

**Merge rule for `books.average_rating` / `books.rating_count`:**

1. Prefer Open Library ratings when present.
2. If Google also has ratings, keep the pair with the **higher `rating_count`** (replace both average and count together).
3. Never fabricate ratings. Leave null when no source has a positive count.
4. Do not store full user review text in MVP (PLAN non-goal). Aggregate stars only.

**Pipeline order:** `run_pipeline` → `enrich_openlibrary_ratings` → `enrich_google_books` → `enrich_openlibrary_pages` (fill remaining `page_count`) → seed.

**Page count merge:** Google Books first when present; Open Library editions median `number_of_pages` fills nulls only (`overwrite=False`). No separate pacing column — UI/compatibility derive Short/Medium/Long from pages (`<250` / `250–450` / `>450`). Profile `pace` maps to length when `preferredLength` is `any` (`fast`→short, `moderate`→medium, `slow`→long).

## Data Model Direction

Keep the existing frontend contract stable. Add tables that make ingestion safer and more traceable.

### Add `book_sources`

Purpose: track every external provider record matched to a BookLens book.

Suggested columns:

- `book_id text not null references public.books(id) on delete cascade`
- `provider text not null`
- `provider_id text not null`
- `provider_url text`
- `raw_payload jsonb`
- `fetched_at timestamptz not null default now()`
- `created_at timestamptz not null default now()`
- primary key `(provider, provider_id)`
- index `(book_id)`

RLS:

- anon may select only if the table is needed by the frontend
- otherwise keep it server-only for now

### Add `book_isbns`

Purpose: allow reliable cross-provider matching.

Suggested columns:

- `book_id text not null references public.books(id) on delete cascade`
- `isbn text not null`
- `isbn_type text`
- `provider text`
- primary key `(book_id, isbn)`
- unique `(isbn)`

Normalize ISBN strings before insert by removing spaces and hyphens.

### Add `ingestion_runs`

Purpose: make imports auditable and easier to debug.

Suggested columns:

- `id uuid primary key default gen_random_uuid()`
- `provider text not null`
- `mode text not null`
- `started_at timestamptz not null default now()`
- `finished_at timestamptz`
- `status text not null default 'running'`
- `requested_count integer`
- `inserted_count integer`
- `updated_count integer`
- `skipped_count integer`
- `error_count integer`
- `notes text`

This can stay server-only.

## Ingestion Architecture

Use a staged pipeline. Each stage should be runnable on its own and should write inspectable local output.

1. Collect raw provider data.
   - Input: provider API, small configured limit
   - Output: `data/raw/<provider>/*.jsonl` or CSV
   - Rule: preserve raw payloads or enough raw fields to debug

2. Normalize provider records.
   - Input: raw provider files
   - Output: common book candidate records
   - Rule: no dedupe beyond obvious same-provider duplicates

3. Match and merge.
   - Input: normalized records from one or more providers
   - Output: one canonical row per BookLens book, plus provider source mappings
   - Rule: ISBN match wins; otherwise use strict normalized title and author matching

4. Compute recommendations.
   - Input: canonical book rows
   - Output: `books_clean.csv`, `recommendations.csv`, and fixture JSON
   - Rule: keep explainable reason chips

5. Seed Supabase.
   - Input: processed CSVs
   - Output: rows in Supabase
   - Rule: upsert only the current seed set unless an explicit replace flag is added

## Provider Precedence

When two sources disagree, use this precedence unless later data proves otherwise.

- Title: Open Library, then Google Books
- Author: Open Library, then Google Books
- Description: longest useful description after stripping markup
- Publication year: earliest plausible year from Open Library or Google Books
- Page count: Google Books, then other edition-level providers
- Cover URL: Open Library large cover, then Google Books thumbnail if high enough quality
- Tags: union of Open Library subjects and Google Books categories, normalized and capped
- Ratings: provider-specific and optional; never fabricate

## Matching Rules

Implement matching conservatively.

Strong match:

- shared ISBN
- same Open Library work ID
- same provider and provider ID

Medium match:

- normalized title match
- normalized first author match
- publication years within 3 years, when both exist

Weak match:

- title-only match
- category-only match
- fuzzy title match without author

Only auto-merge strong and medium matches. Write weak matches to a review report instead of merging them.

## Recommended Implementation Phases

Completed phases:

1. Phase 10: Real Open Library Seed
2. Phase 11: Provider Identity Tables
3. Phase 12: Google Books Enrichment
4. Phase 13: Popularity Signals

### Phase 10: Real Open Library Seed

Goal: seed Supabase from a real Open Library collection using the existing schema.

Tasks:

1. Make `scripts/collect_openlibrary.py` accept:
   - `--subjects fantasy,science_fiction,...`
   - `--limit-total`
   - `--out data/raw/openlibrary_books.csv`
2. Keep the existing `--contact`, `--limit-per-subject`, and `--sleep-seconds`.
3. Add a Make target:
   - `make collect-openlibrary`
   - `make collect-openlibrary CONTACT=you@example.com`
4. Run:
   - collect Open Library data
   - `uv run python scripts/run_pipeline.py --openlibrary`
   - `uv run python scripts/seed_supabase.py --source csv`
5. Add a quality report file under `data/processed/` with:
   - row counts
   - missing descriptions
   - missing covers
   - missing page counts
   - missing ratings
   - top tags
   - recommendation count

Acceptance criteria:

- At least 100 real Open Library books can be collected with one command.
- Pipeline completes without network after collection.
- Supabase receives real books, tags, and recommendations.
- Frontend shows live Supabase data without code changes.
- Missing page/rating fields are still displayed honestly.

Workflow:

```bash
make collect-openlibrary
make pipeline-openlibrary
make seed-supabase SOURCE=csv   # requires SUPABASE_DB_URL in .env
make web-dev
```

Local env:

- `BOOKLENS_CONTACT_EMAIL` or `CONTACT=...` on the Make command for collection
- `SUPABASE_DB_URL` for seeding (server-only; use Session pooler URI from WSL if direct host fails)
- `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `apps/web/.env.local` for frontend reads

Outputs:

- `data/raw/openlibrary_books.csv`
- `data/processed/books_clean.csv`
- `data/processed/recommendations.csv`
- `data/processed/data_quality_report.txt`

### Phase 11: Provider Identity Tables

Goal: prepare for multiple APIs without losing provenance.

Tasks:

1. Add a Supabase migration for:
   - `book_sources`
   - `book_isbns`
   - `ingestion_runs`
2. Extend `scripts/seed_supabase.py` to optionally seed source mappings.
3. Keep current frontend queries unchanged.
4. Document how provider IDs map to canonical book IDs.

Acceptance criteria:

- Existing app still works.
- Open Library seed creates source records.
- RLS does not expose server-only ingestion details unless intentionally selected.

Implementation notes:

- Migration: `supabase/migrations/20260703150000_provider_identity_tables.sql`
- `book_sources` is populated from each seeded book's `source` + `source_id`
- `book_isbns` schema is ready; rows are added only when seed data includes ISBNs
- `ingestion_runs` records each `seed_supabase.py` attempt with counts and status
- Provenance tables have RLS enabled with **no** anon/authenticated policies

Workflow (unchanged for the frontend):

```bash
make seed-supabase              # JSON fixture
make seed-supabase SOURCE=csv   # processed live CSV
```

### Phase 12: Google Books Enrichment

Goal: enrich existing Open Library records with Google Books metadata.

Tasks:

1. Add `GOOGLE_BOOKS_API_KEY` to `.env.example` as server-only.
2. Add `scripts/enrich_google_books.py`.
3. Match by ISBN when available; otherwise title plus author.
4. Fill missing fields only:
   - page count
   - cover URL
   - description
   - categories/tags
   - publication date/year
5. Write an enrichment report:
   - matched records
   - unmatched records
   - fields improved
   - weak matches skipped

Acceptance criteria:

- No API key enters frontend code.
- Enrichment can run on a small sample first.
- Existing Open Library source IDs are preserved.
- Processed CSVs improve page count and cover coverage.

Implementation notes:

- Script: `scripts/enrich_google_books.py`
- Input default: `data/processed/books_clean.csv`
- Output: `data/processed/books_enriched.csv`
- Report: `data/processed/google_books_enrichment_report.txt`
- `isbns` and `extra_sources` columns are JSON strings for `seed_supabase.py`
- `make seed-supabase SOURCE=csv` prefers `books_enriched.csv` when it is present and newer than `books_clean.csv`
- `LIMIT=N` enriches only the first N rows but still writes the full CSV through unchanged
- Primary `source` / `source_id` stay on the Open Library record; Google Books maps to `extra_sources`

Workflow:

```bash
make pipeline-openlibrary
make enrich-openlibrary-ratings
make enrich-google-books
make enrich-openlibrary-pages
make seed-supabase SOURCE=csv
```

Smoke test:

```bash
make enrich-google-books LIMIT=3
```

### Phase 13: Popularity Signals

Goal: add optional popularity/list context without polluting core metadata.

**Status: implemented (report-only smoke ready; hosted write opt-in).**

Scope:

- May edit: `supabase/migrations/*`, `scripts/*popularity*.py`, `Makefile`, `docs/LIVE_DATA_PLAN.md`, `supabase/README.md`, `.env.example`
- Must not edit: Next.js UI, profile/compatibility components, existing enrichment merge rules, Vercel public env names
- Must not overwrite: `books.title`, `books.author`, `books.description`, `books.page_count`, `books.average_rating`, or `books.rating_count`

#### Provider choice

- **Chosen source:** New York Times Books API bestseller lists only
- **Terms:** Developer Portal non-commercial use; attribution required ([Terms](https://developer.nytimes.com/tou), [FAQ](https://developer.nytimes.com/faq))
- **Quota:** typically 500 requests/day and 5 requests/minute (script defaults to 12s sleep between list calls)
- **Not chosen:** paid commercial licensing, scraping Goodreads, or any source that would overwrite bibliographic fields

#### Delivered artifacts

- Migration: `supabase/migrations/20260713160000_book_popularity_signals.sql`
- Importer: `scripts/import_popularity_signals.py`
- Offline fixture: `scripts/fixtures/nyt_hardcover_fiction_sample.json`
- Make target: `make import-popularity-signals`
- Env placeholder: `NYT_BOOKS_API_KEY` in `.env.example` (server-only)

#### Matching

Auto-import only strong/medium matches from this plan:

- strong: shared ISBN
- medium: normalized title + first author (publication years within 3 when both exist)
- weak: title-only — written to the review report, never auto-imported

Core `books.*` fields are never updated by this importer.

#### Commands

```bash
# Offline smoke (no live API, no DB write)
make import-popularity-signals LIMIT=3 FROM_JSON=scripts/fixtures/nyt_hardcover_fiction_sample.json

# Live API smoke (requires NYT_BOOKS_API_KEY; no DB write)
make import-popularity-signals LIMIT=3

# After migration apply + explicit approval only
make import-popularity-signals LIMIT=3 WRITE_DB=1
```

Outputs:

- `data/processed/popularity_signals_report.json`
- `data/processed/popularity_signals_report.txt`

Acceptance criteria:

- Popularity imports do not overwrite core book fields.
- Unmatched popularity rows are reported.
- Frontend remains usable if popularity data is absent.
- Migration is idempotent/reviewable and does not expose server-only raw payloads through anon policies.
- Smoke import can run on a tiny sample before any larger import.

Validation:

```bash
uv run ruff check scripts/
make pipeline-demo
cd apps/web && npm run lint
cd apps/web && npm run build
```

Hosted DB verification after applying the migration/import:

```sql
select count(*) from public.book_popularity_signals;
select provider, list_name, count(*) from public.book_popularity_signals group by provider, list_name order by count(*) desc;
```

### Phase 14: Refresh Workflow

Goal: make repeat imports boring and safe.

Scope:

- May edit: `Makefile`, `modal_app.py`, import/enrichment scripts, `docs/DEPLOYMENT.md`, `docs/LOCAL_DEV_WSL_CURSOR.md`, `supabase/README.md`, `docs/LIVE_DATA_PLAN.md`
- Must not edit: frontend routes/components except docs links if absolutely necessary
- Must not commit: `data/raw/*`, `data/processed/*`, `.env`, `.env.local`

Preflight reads:

- `Makefile`
- `modal_app.py`
- `scripts/collect_openlibrary.py`
- `scripts/run_pipeline.py`
- `scripts/enrich_openlibrary_ratings.py`
- `scripts/enrich_google_books.py`
- `scripts/enrich_openlibrary_pages.py`
- `scripts/seed_supabase.py`
- `docs/DEPLOYMENT.md`

Tasks:

1. Add `make live-seed-small`.
2. Add `make live-seed-openlibrary`.
3. Add dry-run flags to import scripts.
4. Add import summaries to `ingestion_runs`.
5. Document the hosted Supabase workflow.
6. Ensure Make targets run the expected order:
   - collect
   - pipeline
   - Open Library ratings
   - Google Books enrichment when key is present
   - Open Library pages
   - seed
7. For `live-seed-small`, use conservative defaults (`LIMIT_TOTAL=5`, `LIMIT_PER_SUBJECT=1`, optional `LIMIT=3` enrichers).
8. For `live-seed-openlibrary`, use the configured defaults unless caller overrides `LIMIT_TOTAL`, `LIMIT_PER_SUBJECT`, or `SUBJECTS`.
9. If adding `--dry-run`, it must preview work and write reports without changing Supabase.
10. If `seed_supabase.py` gets `--dry-run`, it must not open a write transaction or mutate hosted rows.

Acceptance criteria:

- Small live seed can be tested before a larger import.
- Every import has a summary.
- Re-running imports is idempotent.
- No raw data or secrets are committed.
- Failure at any stage leaves a readable report or console summary with the failing stage.
- Hosted Supabase seed count can be verified with SQL before and after.

Validation:

```bash
uv run ruff check scripts/
make pipeline-demo
make live-seed-small   # only if CONTACT/SUPABASE_DB_URL are configured and the project owner wants a live smoke write
cd apps/web && npm run lint
cd apps/web && npm run build
```

If live writes are skipped, say so in the handoff and include the exact command the project owner should run.

### Phase 15: Scalable Read Models

Goal: prepare the app architecture for catalogs that are too large to load into the browser.

Scope:

- May edit: Supabase migrations, server-side data loaders under `apps/web/src/lib`, app routes that currently call `loadBookLensData`, docs
- Must preserve: fixture fallback, `/books/[id]`, `/explore`, `/analytics`, `/compatibility`, `/profile`
- Must not add: FastAPI, a separate backend service, Supabase Auth, browser-side service keys, provider API calls from the browser

Preflight reads:

- `apps/web/src/lib/load-booklens-data.ts`
- `apps/web/src/lib/booklens-data.ts`
- `apps/web/src/components/book-explorer.tsx`
- `apps/web/src/components/analytics-section.tsx`
- `apps/web/src/components/compatibility-page.tsx`
- `supabase/migrations/*initial*schema.sql`
- `supabase/migrations/20260703150000_provider_identity_tables.sql`

Tasks:

1. Add server-side/paginated book reads:
   - search query
   - tag filters
   - year/page/rating filters
   - sort
   - limit/offset or cursor pagination
2. Add supporting SQL indexes or RPC functions.
3. Keep the current small fixture fallback for local development.
4. Replace client-side all-books filtering with server-backed result pages when Supabase is configured.
5. Keep detail pages fetching only:
   - one selected book
   - its tags
   - its top recommendations
6. Move analytics to precomputed aggregate reads if live row counts become large.
7. Keep small fixture mode client-side so local/demo usage still works without Supabase.
8. Add bounded query defaults:
   - default page size no larger than 50
   - maximum page size no larger than 100
   - deterministic sort order for pagination
9. Add database indexes or RPC functions in the same phase as the query paths that need them.
10. Do not introduce full-catalog JSON payloads in server responses.

Acceptance criteria:

- The app does not need to load the full catalog for explorer search.
- Query responses are bounded and paginated.
- Existing UX remains usable for small fixture fallback.
- Database indexes match the filter and sort paths used by the UI.
- The plan remains compatible with million-book catalogs.
- Detail and compatibility pages never fetch the entire catalog unless running in fixture fallback mode.
- Analytics reads aggregate snapshots or bounded summaries, not all book rows, once live counts are large.

Validation:

```bash
cd apps/web && npm run lint
cd apps/web && npm run build
```

Manual checks:

- `/explore` loads first page only when Supabase is configured.
- Search, include tags, exclude tags, year/page/rating filters, and pagination compose correctly.
- `/books/[id]` fetches one book plus recommendations.
- Fixture fallback still works with no Supabase env vars.
- Network payloads stay bounded as the live catalog grows.

## Environment Variables

Add these only as needed.

```bash
# Required for Open Library collection
BOOKLENS_CONTACT_EMAIL=

# Required for Supabase seeding
SUPABASE_DB_URL=

# Optional for Google Books enrichment
GOOGLE_BOOKS_API_KEY=

# Optional for popularity/bestseller enrichment
NYT_BOOKS_API_KEY=
```

All provider API keys are server-only. Do not prefix them with `NEXT_PUBLIC_`.

## Commands To Target

Planned command shape:

```bash
make collect-openlibrary
make pipeline-openlibrary
make enrich-openlibrary-ratings
make enrich-google-books
make enrich-openlibrary-pages
make import-popularity-signals LIMIT=3
make seed-supabase SOURCE=csv
make verify
```

Later:

```bash
uv run python scripts/enrich_google_books.py --input data/processed/books_clean.csv --output data/processed/books_enriched.csv
make live-seed-small
make live-seed-openlibrary
```

Million-book architecture target:

```text
batch ingestion -> staging/provenance -> canonical books -> indexed read models -> paginated frontend
```

## Guardrails

- Keep `.env`, `data/raw/`, and `data/processed/` ignored.
- Do not commit generated live data.
- Treat `apps/web/src/data/*.sample.json` as committed fixture data. Do not replace it with a large live dump unless the project owner explicitly asks.
- Do not add third-party API calls to browser code.
- Do not store server-only keys in Vercel unless the code path truly runs server-only.
- Do not bulk-harvest APIs. Use small, respectful imports and cache raw responses.
- Do not silently merge weak matches.
- Do not fabricate ratings, page counts, ISBNs, or publication years.
- Keep fixture fallback working.
- Preserve unrelated user/Cursor changes. If the working tree is dirty, only edit files in the current phase scope.
- Prefer reports and row-count verification over guessing whether a live import worked.

## Phase 10 Cursor Prompt

```text
Read docs/DESIGN.md, docs/PLAN.md, docs/LIVE_DATA_PLAN.md, scripts/collect_openlibrary.py, scripts/run_pipeline.py, scripts/seed_supabase.py, Makefile, and supabase/README.md.

Implement Phase 10 only: Real Open Library Seed.

Goal:
Make it easy to collect a modest real Open Library dataset, run the existing pipeline from that collected data, and seed Supabase. Keep the frontend unchanged.

Scope:
- Do not add Google Books yet.
- Do not add NYT or other APIs yet.
- Do not add FastAPI, Modal, LiteLLM, Auth, Storage, or frontend writes.
- Do not commit generated files under data/raw or data/processed.
- Do not expose SUPABASE_DB_URL or API keys to browser code.

Tasks:
1. Update scripts/collect_openlibrary.py:
   - add --subjects as a comma-separated list
   - add --limit-total
   - keep --contact, --limit-per-subject, --sleep-seconds, and --out
   - keep identified User-Agent requests
   - avoid duplicate work keys
2. Add a Makefile target:
   - make collect-openlibrary
   - make collect-openlibrary CONTACT=you@example.com
   - use conservative defaults
3. Ensure the collected CSV can be consumed by:
   - uv run python scripts/run_pipeline.py --openlibrary
4. Ensure the processed CSVs can be seeded by:
   - uv run python scripts/seed_supabase.py --source csv
5. Add or update docs for the live Open Library seed workflow:
   - local .env requirements
   - command order
   - expected outputs
   - generated data policy
6. Add a quality report if scripts/run_pipeline.py does not already emit one clearly enough.

Validation:
- uv run ruff check scripts/
- make pipeline-demo
- If CONTACT is available, run a tiny collection with --limit-per-subject 1 or --limit-total 5.
- Do not run a large API collection during implementation.
- cd apps/web && npm run lint
- cd apps/web && npm run build

Handoff:
Use the Phase Handoff template in docs/PLAN.md.
Include whether live API collection was run, how many rows were collected, and whether Supabase seeding was run against the hosted project.
```
