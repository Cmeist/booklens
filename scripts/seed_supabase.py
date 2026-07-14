"""
Seed or upsert BookLens data into Supabase Postgres.

Reads from committed sample JSON by default, or from processed CSV files.
Requires a server-only database URL. Never run this from browser code.

Examples:
    uv run python scripts/seed_supabase.py
    uv run python scripts/seed_supabase.py --source csv
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
WEB_DATA_DIR = ROOT / "apps" / "web" / "src" / "data"
PROCESSED_DIR = ROOT / "data" / "processed"

BOOK_UPSERT = """
insert into public.books (
  id,
  title,
  author,
  description,
  publication_year,
  decade,
  page_count,
  rating_count,
  average_rating,
  cover_url,
  source,
  source_id
) values (
  %(id)s,
  %(title)s,
  %(author)s,
  %(description)s,
  %(publication_year)s,
  %(decade)s,
  %(page_count)s,
  %(rating_count)s,
  %(average_rating)s,
  %(cover_url)s,
  %(source)s,
  %(source_id)s
)
on conflict (id) do update set
  title = excluded.title,
  author = excluded.author,
  description = excluded.description,
  publication_year = excluded.publication_year,
  decade = excluded.decade,
  page_count = excluded.page_count,
  rating_count = excluded.rating_count,
  average_rating = excluded.average_rating,
  cover_url = excluded.cover_url,
  source = excluded.source,
  source_id = excluded.source_id,
  updated_at = now()
"""

TAG_DELETE = "delete from public.book_tags where book_id = any(%s)"

TAG_INSERT = """
insert into public.book_tags (book_id, tag)
values (%s, %s)
on conflict (book_id, tag) do nothing
"""

RECOMMENDATION_DELETE = """
delete from public.book_recommendations
where book_id = any(%s)
"""

RECOMMENDATION_UPSERT = """
insert into public.book_recommendations (
  book_id,
  similar_book_id,
  score,
  reasons
) values (
  %s,
  %s,
  %s,
  %s
)
on conflict (book_id, similar_book_id) do update set
  score = excluded.score,
  reasons = excluded.reasons
"""

BOOK_SOURCE_UPSERT = """
insert into public.book_sources (
  book_id,
  provider,
  provider_id,
  provider_url,
  raw_payload,
  fetched_at
) values (
  %(book_id)s,
  %(provider)s,
  %(provider_id)s,
  %(provider_url)s,
  %(raw_payload)s,
  now()
)
on conflict (provider, provider_id) do update set
  book_id = excluded.book_id,
  provider_url = excluded.provider_url,
  fetched_at = excluded.fetched_at
"""

BOOK_ISBN_UPSERT = """
insert into public.book_isbns (
  book_id,
  isbn,
  isbn_type,
  provider
) values (
  %s,
  %s,
  %s,
  %s
)
on conflict (isbn) do nothing
"""

INGESTION_RUN_INSERT = """
insert into public.ingestion_runs (
  id,
  provider,
  mode,
  status,
  requested_count,
  started_at
) values (
  %s,
  %s,
  %s,
  'running',
  %s,
  %s
)
"""

INGESTION_RUN_FINISH = """
update public.ingestion_runs
set
  finished_at = %s,
  status = %s,
  inserted_count = %s,
  updated_count = %s,
  skipped_count = %s,
  error_count = %s,
  notes = %s
where id = %s
"""

EXISTING_BOOK_IDS = "select id from public.books where id = any(%s)"

BOOK_PAYLOAD_KEYS = {
    "id",
    "title",
    "author",
    "description",
    "publication_year",
    "decade",
    "page_count",
    "rating_count",
    "average_rating",
    "cover_url",
    "source",
    "source_id",
}


def get_database_url() -> str:
    load_dotenv(ROOT / ".env")
    database_url = os.getenv("SUPABASE_DB_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "SUPABASE_DB_URL is required for seeding. "
            "Set it in .env using the server-only Postgres connection string."
        )
    return database_url


def nullable_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def description_text(value: Any) -> str:
    return nullable_text(value) or ""


def nullable_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return int(float(value))


def nullable_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return float(value)


def parse_tags(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(tag).strip() for tag in value if str(tag).strip()]
    return [tag.strip() for tag in str(value).split(";") if tag.strip()]


def normalize_isbn(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", value).upper()


def parse_isbns(value: Any, provider: str | None) -> list[dict[str, str | None]]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    if isinstance(value, list):
        records = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = []
        records = parsed_value if isinstance(parsed_value, list) else []
    else:
        return []

    parsed: list[dict[str, str | None]] = []
    for item in records:
        if isinstance(item, dict):
            raw_isbn = nullable_text(item.get("isbn"))
            isbn_type = nullable_text(item.get("isbnType") or item.get("isbn_type"))
            isbn_provider = nullable_text(item.get("provider")) or provider
        else:
            raw_isbn = nullable_text(item)
            isbn_type = None
            isbn_provider = provider

        if not raw_isbn:
            continue
        isbn = normalize_isbn(raw_isbn)
        if not isbn:
            continue
        parsed.append(
            {
                "isbn": isbn,
                "isbn_type": isbn_type,
                "provider": isbn_provider,
            }
        )
    return parsed


def parse_extra_sources(value: Any) -> list[dict[str, str | None]]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    if isinstance(value, list):
        records = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = []
        records = parsed_value if isinstance(parsed_value, list) else []
    else:
        return []

    parsed: list[dict[str, str | None]] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        provider = nullable_text(item.get("provider"))
        provider_id = nullable_text(item.get("provider_id") or item.get("providerId"))
        if not provider or not provider_id:
            continue
        parsed.append(
            {
                "provider": provider,
                "provider_id": provider_id,
                "provider_url": nullable_text(item.get("provider_url") or item.get("providerUrl"))
                or provider_url_for(provider, provider_id),
            }
        )
    return parsed


def provider_url_for(provider: str | None, provider_id: str | None) -> str | None:
    if not provider or not provider_id:
        return None
    if provider == "openlibrary":
        if provider_id.startswith("/"):
            return f"https://openlibrary.org{provider_id}"
        return f"https://openlibrary.org/works/{provider_id}"
    if provider == "googlebooks":
        return f"https://books.google.com/books?id={provider_id}"
    return None


def infer_run_provider(books: list[dict[str, Any]], mode: str) -> str:
    sources = {book["source"] for book in books if book.get("source")}
    if len(sources) == 1:
        return next(iter(sources))
    if mode == "json":
        return "fixture"
    return "mixed"


def book_upsert_payload(book: dict[str, Any]) -> dict[str, Any]:
    return {key: book.get(key) for key in BOOK_PAYLOAD_KEYS}


def book_row_from_json(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": nullable_text(record["id"]),
        "title": nullable_text(record["title"]),
        "author": nullable_text(record["author"]),
        "description": description_text(record.get("description")),
        "publication_year": nullable_int(record.get("publicationYear")),
        "decade": nullable_text(record.get("decade")),
        "page_count": nullable_int(record.get("pageCount")),
        "rating_count": nullable_int(record.get("ratingCount")),
        "average_rating": nullable_float(record.get("averageRating")),
        "cover_url": nullable_text(record.get("coverUrl")),
        "source": nullable_text(record["source"]),
        "source_id": nullable_text(record["sourceId"]),
        "tags": parse_tags(record.get("tags")),
        "isbns": parse_isbns(record.get("isbns"), nullable_text(record.get("source"))),
        "extra_sources": parse_extra_sources(record.get("extra_sources")),
    }


def book_row_from_csv(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": nullable_text(record["id"]),
        "title": nullable_text(record["title"]),
        "author": nullable_text(record["author"]),
        "description": description_text(record.get("description")),
        "publication_year": nullable_int(record.get("publication_year")),
        "decade": nullable_text(record.get("decade")),
        "page_count": nullable_int(record.get("page_count")),
        "rating_count": nullable_int(record.get("rating_count")),
        "average_rating": nullable_float(record.get("average_rating")),
        "cover_url": nullable_text(record.get("cover_url")),
        "source": nullable_text(record["source"]),
        "source_id": nullable_text(record["source_id"]),
        "tags": parse_tags(record.get("tags")),
        "isbns": parse_isbns(record.get("isbns"), nullable_text(record.get("source"))),
        "extra_sources": parse_extra_sources(record.get("extra_sources")),
    }


def load_json_source() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    books_path = WEB_DATA_DIR / "books.sample.json"
    recommendations_path = WEB_DATA_DIR / "recommendations.sample.json"

    books_raw = json.loads(books_path.read_text(encoding="utf-8"))
    recommendations_raw = json.loads(recommendations_path.read_text(encoding="utf-8"))

    books = [book_row_from_json(record) for record in books_raw]
    recommendations = [
        {
            "book_id": record["bookId"],
            "similar_book_id": record["similarBookId"],
            "score": float(record["score"]),
            "reasons": list(record["reasons"]),
        }
        for record in recommendations_raw
    ]
    return books, recommendations


def load_csv_source() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    enriched_path = PROCESSED_DIR / "books_enriched.csv"
    clean_path = PROCESSED_DIR / "books_clean.csv"
    books_path = clean_path
    if enriched_path.exists() and clean_path.exists():
        enriched_rows = sum(1 for _ in enriched_path.open(encoding="utf-8")) - 1
        clean_rows = sum(1 for _ in clean_path.open(encoding="utf-8")) - 1
        # Prefer enriched only when it covers the full clean set (not a stale partial).
        if enriched_rows >= clean_rows and enriched_path.stat().st_mtime >= clean_path.stat().st_mtime:
            books_path = enriched_path
        elif enriched_rows < clean_rows:
            print(
                f"Using {clean_path} ({clean_rows} rows); "
                f"{enriched_path} is a partial enrich ({enriched_rows} rows). "
                "Run make enrich-google-books for a full enriched set."
            )
        else:
            print(
                f"Using {clean_path} because it is newer than {enriched_path}. "
                "Run make enrich-google-books to refresh enrichment."
            )
    elif enriched_path.exists():
        books_path = enriched_path
    recommendations_path = PROCESSED_DIR / "recommendations.csv"

    if not books_path.exists():
        raise FileNotFoundError(
            f"Processed books file not found: {books_path}. "
            "Run make pipeline-demo or make pipeline-openlibrary first."
        )

    books_df = pd.read_csv(books_path)
    books = [book_row_from_csv(record) for record in books_df.to_dict(orient="records")]

    recommendations: list[dict[str, Any]] = []
    if recommendations_path.exists():
        recommendations_df = pd.read_csv(recommendations_path)
        for record in recommendations_df.to_dict(orient="records"):
            reasons = [
                part.strip()
                for part in str(record.get("reasons", "")).split(";")
                if part.strip()
            ]
            recommendations.append(
                {
                    "book_id": record["book_id"],
                    "similar_book_id": record["similar_book_id"],
                    "score": float(record["score"]),
                    "reasons": reasons,
                }
            )

    return books, recommendations


def start_ingestion_run(
    database_url: str,
    *,
    run_id: uuid.UUID,
    provider: str,
    mode: str,
    requested_count: int,
    started_at: datetime,
) -> None:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                INGESTION_RUN_INSERT,
                (run_id, provider, mode, requested_count, started_at),
            )
        conn.commit()


def finish_ingestion_run(
    database_url: str,
    *,
    run_id: uuid.UUID,
    status: str,
    inserted_count: int,
    updated_count: int,
    skipped_count: int,
    error_count: int,
    notes: str,
) -> None:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                INGESTION_RUN_FINISH,
                (
                    datetime.now(UTC),
                    status,
                    inserted_count,
                    updated_count,
                    skipped_count,
                    error_count,
                    notes,
                    run_id,
                ),
            )
        conn.commit()


def seed_supabase(
    books: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    *,
    mode: str,
) -> None:
    database_url = get_database_url()
    seeded_book_ids = [book["id"] for book in books if book.get("id")]
    run_id = uuid.uuid4()
    run_provider = infer_run_provider(books, mode)
    started_at = datetime.now(UTC)

    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    source_count = 0
    isbn_count = 0
    isbn_skipped_count = 0
    notes: list[str] = []

    start_ingestion_run(
        database_url,
        run_id=run_id,
        provider=run_provider,
        mode=mode,
        requested_count=len(books),
        started_at=started_at,
    )

    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                existing_book_ids: set[str] = set()
                if seeded_book_ids:
                    cur.execute(EXISTING_BOOK_IDS, (seeded_book_ids,))
                    existing_book_ids = {row[0] for row in cur.fetchall()}

                tag_rows: list[tuple[str, str]] = []
                source_rows: list[dict[str, Any]] = []
                isbn_rows: list[tuple[str, str, str | None, str | None]] = []

                for book in books:
                    book_id = book.get("id")
                    if not book_id:
                        skipped_count += 1
                        continue

                    tags = book.get("tags", [])
                    isbns = book.get("isbns", [])
                    extra_sources = book.get("extra_sources", [])
                    source = book.get("source")
                    source_id = book.get("source_id")

                    cur.execute(BOOK_UPSERT, book_upsert_payload(book))
                    if book_id in existing_book_ids:
                        updated_count += 1
                    else:
                        inserted_count += 1

                    tag_rows.extend((book_id, tag) for tag in tags)

                    if source and source_id:
                        source_rows.append(
                            {
                                "book_id": book_id,
                                "provider": source,
                                "provider_id": source_id,
                                "provider_url": provider_url_for(source, source_id),
                                "raw_payload": None,
                            },
                        )

                    for extra_source in extra_sources:
                        source_rows.append(
                            {
                                "book_id": book_id,
                                "provider": extra_source["provider"],
                                "provider_id": extra_source["provider_id"],
                                "provider_url": extra_source.get("provider_url"),
                                "raw_payload": None,
                            },
                        )

                    for isbn_record in isbns:
                        isbn_rows.append(
                            (
                                book_id,
                                isbn_record["isbn"],
                                isbn_record.get("isbn_type"),
                                isbn_record.get("provider"),
                            ),
                        )

                if seeded_book_ids:
                    cur.execute(TAG_DELETE, (seeded_book_ids,))

                if tag_rows:
                    cur.executemany(TAG_INSERT, tag_rows)

                if source_rows:
                    cur.executemany(BOOK_SOURCE_UPSERT, source_rows)
                    source_count = len(source_rows)

                if isbn_rows:
                    cur.executemany(BOOK_ISBN_UPSERT, isbn_rows)
                    if cur.rowcount >= 0:
                        isbn_count = cur.rowcount
                        isbn_skipped_count = len(isbn_rows) - isbn_count
                    else:
                        isbn_count = len(isbn_rows)

                if seeded_book_ids:
                    cur.execute(RECOMMENDATION_DELETE, (seeded_book_ids,))

                if recommendations:
                    cur.executemany(
                        RECOMMENDATION_UPSERT,
                        [
                            (
                                recommendation["book_id"],
                                recommendation["similar_book_id"],
                                recommendation["score"],
                                recommendation["reasons"],
                            )
                            for recommendation in recommendations
                        ],
                    )

            conn.commit()
    except Exception as exc:
        error_count += 1
        notes.append(str(exc))
        summary = (
            f"book_sources={source_count}; book_isbns={isbn_count}; "
            f"book_isbns_skipped={isbn_skipped_count}; "
            f"recommendations={len(recommendations)}; errors={' | '.join(notes[:5])}"
        )
        try:
            finish_ingestion_run(
                database_url,
                run_id=run_id,
                status="failed",
                inserted_count=inserted_count,
                updated_count=updated_count,
                skipped_count=skipped_count,
                error_count=error_count,
                notes=summary,
            )
        except Exception:
            pass
        raise

    status = "succeeded"
    summary = (
        f"book_sources={source_count}; book_isbns={isbn_count}; "
        f"book_isbns_skipped={isbn_skipped_count}; recommendations={len(recommendations)}"
    )
    finish_ingestion_run(
        database_url,
        run_id=run_id,
        status=status,
        inserted_count=inserted_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        error_count=error_count,
        notes=summary,
    )

    print(
        "Seeded "
        f"{len(books)} books, {source_count} book_sources rows, "
        f"{isbn_count} book_isbns rows "
        f"({isbn_skipped_count} duplicate ISBNs skipped), "
        f"and {len(recommendations)} recommendations "
        f"into Supabase (ingestion_run={run_id}, status={status})."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed BookLens data into Supabase Postgres.")
    parser.add_argument(
        "--source",
        choices=["json", "csv"],
        default="json",
        help="Load seed data from committed sample JSON or processed CSV files.",
    )
    args = parser.parse_args()

    if args.source == "json":
        books, recommendations = load_json_source()
    else:
        books, recommendations = load_csv_source()

    if not books:
        print("No books found to seed.", file=sys.stderr)
        sys.exit(1)

    seed_supabase(books, recommendations, mode=args.source)


if __name__ == "__main__":
    main()
