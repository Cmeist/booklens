-- BookLens popularity signals: optional bestseller/list context, separate from core books.

create table if not exists public.book_popularity_signals (
  id uuid primary key default gen_random_uuid(),
  book_id text not null references public.books (id) on delete cascade,
  provider text not null,
  provider_id text,
  list_name text not null,
  rank integer,
  published_at date,
  matched_on text,
  raw_payload jsonb,
  created_at timestamptz not null default now(),
  constraint book_popularity_signals_rank_positive_check
    check (rank is null or rank > 0)
);

create index if not exists book_popularity_signals_book_id_idx
  on public.book_popularity_signals (book_id);

create index if not exists book_popularity_signals_provider_list_published_idx
  on public.book_popularity_signals (provider, list_name, published_at);

create index if not exists book_popularity_signals_provider_id_idx
  on public.book_popularity_signals (provider_id)
  where provider_id is not null;

-- Idempotent re-import for the same list week + provider book id.
create unique index if not exists book_popularity_signals_provider_list_date_id_uidx
  on public.book_popularity_signals (provider, list_name, published_at, provider_id)
  where provider_id is not null;

alter table public.book_popularity_signals enable row level security;

-- Server-only: no anon/authenticated policies. Importer uses SUPABASE_DB_URL.
revoke all on public.book_popularity_signals from anon, authenticated;
