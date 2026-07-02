-- BookLens initial schema: books, tags, recommendations, views, and read-only RLS.

create table if not exists public.books (
  id text primary key,
  title text not null,
  author text not null,
  description text not null default '',
  publication_year integer,
  decade text,
  page_count integer,
  rating_count integer,
  average_rating numeric(4, 2),
  cover_url text,
  source text not null,
  source_id text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint books_publication_year_range_check
    check (publication_year is null or (publication_year >= 1400 and publication_year <= 2100)),
  constraint books_page_count_positive_check
    check (page_count is null or page_count > 0),
  constraint books_average_rating_range_check
    check (average_rating is null or (average_rating >= 0 and average_rating <= 5)),
  constraint books_rating_count_nonnegative_check
    check (rating_count is null or rating_count >= 0),
  constraint books_source_source_id_unique unique (source, source_id)
);

create table if not exists public.book_tags (
  book_id text not null references public.books (id) on delete cascade,
  tag text not null,
  primary key (book_id, tag)
);

create index if not exists book_tags_tag_idx on public.book_tags (tag);

create table if not exists public.book_recommendations (
  book_id text not null references public.books (id) on delete cascade,
  similar_book_id text not null references public.books (id) on delete cascade,
  score numeric(7, 4) not null,
  reasons text[] not null default '{}',
  primary key (book_id, similar_book_id),
  constraint book_recommendations_distinct_books_check
    check (book_id <> similar_book_id),
  constraint book_recommendations_score_nonnegative_check
    check (score >= 0)
);

create or replace view public.books_with_tags as
select
  b.id,
  b.title,
  b.author,
  b.description,
  b.publication_year,
  b.decade,
  b.page_count,
  b.rating_count,
  b.average_rating,
  b.cover_url,
  b.source,
  b.source_id,
  b.created_at,
  b.updated_at,
  coalesce(
    array_agg(bt.tag order by bt.tag) filter (where bt.tag is not null),
    '{}'::text[]
  ) as tags
from public.books b
left join public.book_tags bt on bt.book_id = b.id
group by b.id;

create or replace view public.top_tags as
select
  bt.tag,
  count(*)::integer as book_count
from public.book_tags bt
group by bt.tag
order by book_count desc, bt.tag asc;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists books_set_updated_at on public.books;

create trigger books_set_updated_at
before update on public.books
for each row
execute function public.set_updated_at();

alter table public.books enable row level security;
alter table public.book_tags enable row level security;
alter table public.book_recommendations enable row level security;

drop policy if exists "anon_select_books" on public.books;
create policy "anon_select_books"
on public.books
for select
to anon
using (true);

drop policy if exists "anon_select_book_tags" on public.book_tags;
create policy "anon_select_book_tags"
on public.book_tags
for select
to anon
using (true);

drop policy if exists "anon_select_book_recommendations" on public.book_recommendations;
create policy "anon_select_book_recommendations"
on public.book_recommendations
for select
to anon
using (true);

grant usage on schema public to anon, authenticated;
grant select on public.books to anon, authenticated;
grant select on public.book_tags to anon, authenticated;
grant select on public.book_recommendations to anon, authenticated;
grant select on public.books_with_tags to anon, authenticated;
grant select on public.top_tags to anon, authenticated;

alter view public.books_with_tags set (security_invoker = true);
alter view public.top_tags set (security_invoker = true);
