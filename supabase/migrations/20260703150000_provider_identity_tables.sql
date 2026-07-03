-- BookLens provider identity tables: provenance, ISBN matching, ingestion audit.

create table if not exists public.book_sources (
  book_id text not null references public.books (id) on delete cascade,
  provider text not null,
  provider_id text not null,
  provider_url text,
  raw_payload jsonb,
  fetched_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  primary key (provider, provider_id)
);

create index if not exists book_sources_book_id_idx on public.book_sources (book_id);

create table if not exists public.book_isbns (
  book_id text not null references public.books (id) on delete cascade,
  isbn text not null,
  isbn_type text,
  provider text,
  created_at timestamptz not null default now(),
  primary key (book_id, isbn),
  constraint book_isbns_isbn_unique unique (isbn)
);

create index if not exists book_isbns_book_id_idx on public.book_isbns (book_id);

create table if not exists public.ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  mode text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running',
  requested_count integer,
  inserted_count integer,
  updated_count integer,
  skipped_count integer,
  error_count integer,
  notes text,
  constraint ingestion_runs_status_check
    check (status in ('running', 'succeeded', 'failed'))
);

create index if not exists ingestion_runs_started_at_idx
  on public.ingestion_runs (started_at desc);

alter table public.book_sources enable row level security;
alter table public.book_isbns enable row level security;
alter table public.ingestion_runs enable row level security;

-- Server-only provenance tables: no anon/authenticated policies.
-- The seed script connects with SUPABASE_DB_URL (postgres role).

revoke all on public.book_sources from anon, authenticated;
revoke all on public.book_isbns from anon, authenticated;
revoke all on public.ingestion_runs from anon, authenticated;
