# BookLens Deployment

BookLens uses two deployment surfaces:

- **Vercel** serves the Next.js web app from `apps/web`.
- **Modal** runs server-only Python data refresh jobs that collect, enrich, and seed Supabase.

Supabase remains the shared data layer. Vercel reads public data through the anon key. Modal uses server-only secrets to refresh data.

## Vercel Web App

Use Vercel for the public web URL.

### Project Settings

In the Vercel dashboard:

- Root Directory: `apps/web`
- Framework Preset: `Next.js`
- Install Command: `npm install`
- Build Command: `npm run build`
- Output Directory: `.next`

`apps/web/vercel.json` commits the framework, install, and build command defaults for the web app root.

### Vercel Environment Variables

Set these in Vercel for Production and Preview as needed:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

Do **not** set these in Vercel:

```bash
SUPABASE_DB_URL=
SUPABASE_SERVICE_ROLE_KEY=
GOOGLE_BOOKS_API_KEY=
BOOKLENS_CONTACT_EMAIL=
```

Those are server-only values for local scripts or Modal.

### Deploy

From the repo root:

```bash
cd apps/web
npx vercel login
npx vercel link
npx vercel --prod
```

Or use:

```bash
make vercel-deploy
```

After deploy, open the Vercel URL and check:

- `/`
- `/explore`
- `/analytics`
- `/books/<known-book-id>`

If public Supabase vars are missing or the Supabase fetch fails, the app uses committed sample fixtures.

## Modal Data Jobs

Use Modal for server-only refresh work:

```text
Open Library collection -> pipeline -> optional Google Books enrichment -> Supabase seed
```

The Modal app is defined in `modal_app.py` with app name `booklens-data-jobs`.

### Install And Authenticate

From the repo root:

```bash
uv sync
uv run modal token new
```

### Create The Modal Secret

Create a Modal secret named `booklens-secrets`:

```bash
uv run modal secret create booklens-secrets \
  SUPABASE_DB_URL='postgresql://...' \
  BOOKLENS_CONTACT_EMAIL='you@example.com' \
  GOOGLE_BOOKS_API_KEY='...'
```

`GOOGLE_BOOKS_API_KEY` is only required when `enrich_google_books=true`.

### Deploy The Modal App

```bash
make modal-deploy
```

Equivalent:

```bash
uv run modal deploy modal_app.py
```

### Run A Small Refresh

Smoke test first:

```bash
uv run modal run modal_app.py --limit-total 5 --limit-per-subject 1
```

Then run the default refresh:

```bash
make modal-refresh
```

By default this collects up to `LIMIT_TOTAL=120` books and enriches with Google Books.

Override limits:

```bash
LIMIT_TOTAL=25 LIMIT_PER_SUBJECT=5 make modal-refresh
```

### What Modal Seeds

The Modal job:

1. writes `data/raw/openlibrary_books.csv` inside the remote container
2. runs the normal Python pipeline
3. optionally writes `data/processed/books_enriched.csv`
4. seeds Supabase with `SOURCE=csv` behavior
5. returns a summary with collected rows, seeded books, recommendations, and enrichment stats

Generated data inside Modal is ephemeral. Supabase is the durable output.

## Verification

Before deploying:

```bash
uv run ruff check scripts/ modal_app.py
cd apps/web && npm run lint
cd apps/web && npm run build
```

After deploying:

```sql
select count(*) from public.books;
select provider, count(*) from public.book_sources group by provider;
select status, inserted_count, updated_count, error_count, notes
from public.ingestion_runs
order by started_at desc
limit 5;
```

Then visit the Vercel URL and confirm the header shows `Data: Supabase`.

## Notes

- Vercel hosts the web app. Modal does not serve the frontend.
- Modal should not receive `NEXT_PUBLIC_*` values unless a future job actually needs them.
- Vercel should not receive `SUPABASE_DB_URL`, service-role keys, or provider API keys.
- If you rotate Supabase or Google keys, update the Modal secret and Vercel project settings separately.
