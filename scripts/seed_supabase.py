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
import sys
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

TAG_DELETE = "delete from public.book_tags where book_id = %s"

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
    books_path = PROCESSED_DIR / "books_clean.csv"
    recommendations_path = PROCESSED_DIR / "recommendations.csv"

    if not books_path.exists():
        raise FileNotFoundError(f"Processed books file not found: {books_path}")

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


def seed_supabase(books: list[dict[str, Any]], recommendations: list[dict[str, Any]]) -> None:
    database_url = get_database_url()
    seeded_book_ids = [book["id"] for book in books]

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for book in books:
                tags = book.pop("tags")
                cur.execute(BOOK_UPSERT, book)
                cur.execute(TAG_DELETE, (book["id"],))
                for tag in tags:
                    cur.execute(TAG_INSERT, (book["id"], tag))

            if seeded_book_ids:
                cur.execute(RECOMMENDATION_DELETE, (seeded_book_ids,))

            for recommendation in recommendations:
                cur.execute(
                    RECOMMENDATION_UPSERT,
                    (
                        recommendation["book_id"],
                        recommendation["similar_book_id"],
                        recommendation["score"],
                        recommendation["reasons"],
                    ),
                )

        conn.commit()

    print(f"Seeded {len(books)} books and {len(recommendations)} recommendations into Supabase.")


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

    seed_supabase(books, recommendations)


if __name__ == "__main__":
    main()
