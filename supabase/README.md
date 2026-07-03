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

- `SUPABASE_DB_URL` — Postgres connection string used by `scripts/seed_supabase.py`
- `SUPABASE_SERVICE_ROLE_KEY` — optional for future server-only tooling
- `SUPABASE_URL` — optional server-side project URL
- `SUPABASE_ANON_KEY` — optional server-side anon key copy

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

If you are not using the CLI, paste the contents of `migrations/20260302000000_initial_booklens_schema.sql` into the Supabase SQL editor and run it once.

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
make seed-supabase SOURCE=csv
```

See `docs/LIVE_DATA_PLAN.md` for the full live-data workflow and quality report details.

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
