# BookLens Supabase

This folder contains the committed Postgres schema for BookLens. Supabase is the intended production data layer; the Next.js app will read public book data with the anon key in Phase 6.

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

### Frontend-safe (browser)

These may be exposed to Next.js client code in Phase 6:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Server-only (seed/import scripts only)

These must never be prefixed with `NEXT_PUBLIC_` and must never ship to browser code:

- `SUPABASE_DB_URL` — Postgres connection string used by `scripts/seed_supabase.py`
- `SUPABASE_SERVICE_ROLE_KEY` — optional for future server-only tooling
- `SUPABASE_URL` — optional server-side project URL
- `SUPABASE_ANON_KEY` — optional server-side anon key copy

For Phase 5 seeding, set `SUPABASE_DB_URL` only.

Example source for the DB URL in the Supabase dashboard:

`Project Settings → Database → Connection string → URI`

Use the direct Postgres connection string, not the pooler URL, unless you know you need pooling for the seed script.

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

The frontend still reads committed JSON fixtures in Phase 5. Seeding Supabase is optional until Phase 6, but this is the supported import path.

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

## Next step

Phase 6 will add frontend Supabase reads with fixture fallback when public env vars are absent.
