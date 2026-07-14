"""Import optional popularity/list signals without touching core book metadata.

Source: New York Times Books API (bestseller lists only).
Non-commercial use; rate limits typically 500 requests/day and 5/minute.
Requires server-only NYT_BOOKS_API_KEY. Never overwrites books.* fields.

Matching (docs/LIVE_DATA_PLAN.md):
  strong  — shared ISBN
  medium  — normalized title + first author (year within 3 when both present)
  weak    — title-only (reported, never auto-imported)

Examples:
  uv run python scripts/import_popularity_signals.py --limit 3
  uv run python scripts/import_popularity_signals.py --limit 5 --lists hardcover-fiction
  uv run python scripts/import_popularity_signals.py --from-json data/raw/nyt_list.json --limit 3
  uv run python scripts/import_popularity_signals.py --limit 3 --write-db
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
import requests
from dotenv import load_dotenv
from psycopg.types.json import Json

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
NYT_LIST_API = "https://api.nytimes.com/svc/books/v3/lists/{date}/{list_name}.json"
PROVIDER = "nyt_books"
DEFAULT_LISTS = ("hardcover-fiction",)
DEFAULT_SLEEP_SECONDS = 12.0

SIGNAL_UPSERT = """
insert into public.book_popularity_signals (
  book_id,
  provider,
  provider_id,
  list_name,
  rank,
  published_at,
  matched_on,
  raw_payload
) values (
  %(book_id)s,
  %(provider)s,
  %(provider_id)s,
  %(list_name)s,
  %(rank)s,
  %(published_at)s,
  %(matched_on)s,
  %(raw_payload)s
)
on conflict (provider, list_name, published_at, provider_id)
where provider_id is not null
do update set
  book_id = excluded.book_id,
  rank = excluded.rank,
  matched_on = excluded.matched_on,
  raw_payload = excluded.raw_payload
"""


@dataclass
class CatalogBook:
    book_id: str
    title: str
    author: str
    publication_year: int | None
    isbns: set[str] = field(default_factory=set)


@dataclass
class ListEntry:
    list_name: str
    published_at: date | None
    rank: int | None
    title: str
    author: str
    isbns: list[str]
    provider_id: str | None
    publication_year: int | None
    raw: dict[str, Any]


@dataclass
class MatchResult:
    status: str  # matched | weak | unmatched
    strength: str | None = None  # strong | medium | weak
    book_id: str | None = None
    matched_on: str | None = None
    catalog_title: str | None = None
    catalog_author: str | None = None


@dataclass
class ImportStats:
    lists_fetched: int = 0
    entries_seen: int = 0
    matched_strong: int = 0
    matched_medium: int = 0
    weak: int = 0
    unmatched: int = 0
    written: int = 0
    api_errors: int = 0


def get_api_key() -> str:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("NYT_BOOKS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "NYT_BOOKS_API_KEY is required for live fetches. "
            "Set it in .env as a server-only variable, or pass --from-json."
        )
    return api_key


def get_database_url() -> str:
    load_dotenv(ROOT / ".env")
    database_url = os.getenv("SUPABASE_DB_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "SUPABASE_DB_URL is required for --write-db. "
            "Set it in .env as a server-only variable."
        )
    return database_url


def nullable_text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def nullable_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_isbn(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", value).upper()


def first_author(author: str | None) -> str:
    if not author:
        return ""
    cleaned = re.sub(r"^(by|and)\s+", "", author.strip(), flags=re.IGNORECASE)
    return cleaned.split(";")[0].split(",")[0].strip()


def parse_isbns_column(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        isbns: list[str] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            raw = nullable_text(item.get("isbn"))
            if not raw:
                continue
            isbn = normalize_isbn(raw)
            if isbn:
                isbns.append(isbn)
        return isbns
    return []


def resolve_books_csv(explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.exists():
            raise FileNotFoundError(f"Books CSV not found: {explicit}")
        return explicit

    enriched = PROCESSED_DIR / "books_enriched.csv"
    clean = PROCESSED_DIR / "books_clean.csv"
    if enriched.exists():
        return enriched
    if clean.exists():
        return clean
    raise FileNotFoundError(
        "No books CSV found. Run make pipeline-demo (and optional enrichment) first, "
        "or pass --books-csv."
    )


def load_catalog(books_csv: Path) -> list[CatalogBook]:
    frame = pd.read_csv(books_csv)
    catalog: list[CatalogBook] = []
    for row in frame.to_dict(orient="records"):
        book_id = nullable_text(row.get("id"))
        title = nullable_text(row.get("title"))
        author = nullable_text(row.get("author"))
        if not book_id or not title or not author:
            continue
        catalog.append(
            CatalogBook(
                book_id=book_id,
                title=title,
                author=author,
                publication_year=nullable_int(row.get("publication_year")),
                isbns=set(parse_isbns_column(row.get("isbns"))),
            )
        )
    return catalog


def build_isbn_index(catalog: list[CatalogBook]) -> dict[str, CatalogBook]:
    index: dict[str, CatalogBook] = {}
    for book in catalog:
        for isbn in book.isbns:
            index.setdefault(isbn, book)
    return index


def build_title_author_index(catalog: list[CatalogBook]) -> dict[tuple[str, str], list[CatalogBook]]:
    index: dict[tuple[str, str], list[CatalogBook]] = {}
    for book in catalog:
        key = (normalize_key(book.title), normalize_key(first_author(book.author)))
        if not key[0] or not key[1]:
            continue
        index.setdefault(key, []).append(book)
    return index


def build_title_index(catalog: list[CatalogBook]) -> dict[str, list[CatalogBook]]:
    index: dict[str, list[CatalogBook]] = {}
    for book in catalog:
        key = normalize_key(book.title)
        if not key:
            continue
        index.setdefault(key, []).append(book)
    return index


def years_compatible(left: int | None, right: int | None) -> bool:
    if left is None or right is None:
        return True
    return abs(left - right) <= 3


def parse_published_date(value: Any) -> date | None:
    text = nullable_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def extract_entry_isbns(book: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for key in ("primary_isbn13", "primary_isbn10"):
        raw = nullable_text(book.get(key))
        if not raw:
            continue
        isbn = normalize_isbn(raw)
        if isbn and isbn not in seen:
            seen.add(isbn)
            values.append(isbn)
    for item in book.get("isbns") or []:
        if not isinstance(item, dict):
            continue
        for key in ("isbn13", "isbn10"):
            raw = nullable_text(item.get(key))
            if not raw:
                continue
            isbn = normalize_isbn(raw)
            if isbn and isbn not in seen:
                seen.add(isbn)
                values.append(isbn)
    return values


def parse_list_payload(payload: dict[str, Any], *, list_name: str) -> list[ListEntry]:
    results = payload.get("results")
    books: list[dict[str, Any]] = []
    published_at: date | None = None
    resolved_list_name = list_name

    if isinstance(results, dict):
        published_at = parse_published_date(results.get("published_date"))
        resolved_list_name = (
            nullable_text(results.get("list_name_encoded"))
            or nullable_text(results.get("list_name"))
            or list_name
        )
        raw_books = results.get("books")
        if isinstance(raw_books, list):
            books = [item for item in raw_books if isinstance(item, dict)]
    elif isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            if published_at is None:
                published_at = parse_published_date(item.get("published_date"))
            details = item.get("book_details")
            if isinstance(details, list) and details:
                detail = details[0] if isinstance(details[0], dict) else {}
                merged = {**detail, **item}
                books.append(merged)
            else:
                books.append(item)

    entries: list[ListEntry] = []
    for book in books:
        title = nullable_text(book.get("title"))
        author = nullable_text(book.get("author"))
        if not title:
            continue
        isbns = extract_entry_isbns(book)
        provider_id = (
            nullable_text(book.get("book_uri"))
            or nullable_text(book.get("primary_isbn13"))
            or (isbns[0] if isbns else None)
        )
        entries.append(
            ListEntry(
                list_name=resolved_list_name,
                published_at=published_at,
                rank=nullable_int(book.get("rank")),
                title=title,
                author=author or "",
                isbns=isbns,
                provider_id=provider_id,
                publication_year=None,
                raw=book,
            )
        )
    return entries


def fetch_nyt_list(
    api_key: str,
    list_name: str,
    *,
    list_date: str = "current",
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
    max_attempts: int = 3,
) -> dict[str, Any]:
    url = NYT_LIST_API.format(date=list_date, list_name=list_name)
    params = {"api-key": api_key}
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 429:
                time.sleep(sleep_seconds * attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise RuntimeError("NYT Books API returned a non-object payload")
            return payload
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            time.sleep(min(sleep_seconds, 2.0) * attempt)
    raise RuntimeError(f"NYT Books API request failed for {list_name}: {last_error}")


def match_entry(
    entry: ListEntry,
    *,
    isbn_index: dict[str, CatalogBook],
    title_author_index: dict[tuple[str, str], list[CatalogBook]],
    title_index: dict[str, list[CatalogBook]],
) -> MatchResult:
    for isbn in entry.isbns:
        book = isbn_index.get(isbn)
        if book is not None:
            return MatchResult(
                status="matched",
                strength="strong",
                book_id=book.book_id,
                matched_on=f"isbn:{isbn}",
                catalog_title=book.title,
                catalog_author=book.author,
            )

    title_key = normalize_key(entry.title)
    author_key = normalize_key(first_author(entry.author))
    if title_key and author_key:
        candidates = title_author_index.get((title_key, author_key), [])
        for book in candidates:
            if years_compatible(entry.publication_year, book.publication_year):
                return MatchResult(
                    status="matched",
                    strength="medium",
                    book_id=book.book_id,
                    matched_on="title+author",
                    catalog_title=book.title,
                    catalog_author=book.author,
                )

    if title_key:
        weak_hits = title_index.get(title_key, [])
        if weak_hits:
            book = weak_hits[0]
            return MatchResult(
                status="weak",
                strength="weak",
                book_id=book.book_id,
                matched_on="title-only",
                catalog_title=book.title,
                catalog_author=book.author,
            )

    return MatchResult(status="unmatched")


def write_report(
    report_path: Path,
    *,
    stats: ImportStats,
    matched: list[dict[str, Any]],
    weak: list[dict[str, Any]],
    unmatched: list[dict[str, Any]],
    meta: dict[str, Any],
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "meta": meta,
        "stats": asdict(stats),
        "matched": matched,
        "weak": weak,
        "unmatched": unmatched,
    }
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    text_path = report_path.with_suffix(".txt")
    lines = [
        "BookLens popularity signals report",
        f"generated_at: {payload['generated_at']}",
        f"provider: {PROVIDER}",
        f"lists: {', '.join(meta.get('lists', []))}",
        f"entries_seen: {stats.entries_seen}",
        f"matched_strong: {stats.matched_strong}",
        f"matched_medium: {stats.matched_medium}",
        f"weak (not imported): {stats.weak}",
        f"unmatched: {stats.unmatched}",
        f"written_to_db: {stats.written}",
        "",
        "Matched (auto-import eligible):",
    ]
    for row in matched[:50]:
        lines.append(
            f"  [{row.get('strength')}] #{row.get('rank')} {row.get('title')} "
            f"/ {row.get('author')} -> {row.get('book_id')} ({row.get('matched_on')})"
        )
    lines.extend(["", "Weak (review only, not imported):"])
    for row in weak[:50]:
        lines.append(
            f"  #{row.get('rank')} {row.get('title')} / {row.get('author')} "
            f"~ {row.get('catalog_title')} / {row.get('catalog_author')}"
        )
    lines.extend(["", "Unmatched:"])
    for row in unmatched[:50]:
        lines.append(f"  #{row.get('rank')} {row.get('title')} / {row.get('author')}")
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_db_rows(rows: list[dict[str, Any]], database_url: str) -> int:
    if not rows:
        return 0
    written = 0
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(SIGNAL_UPSERT, row)
                written += 1
        conn.commit()
    return written


def load_entries_from_json(path: Path, *, list_name: str) -> list[ListEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"--from-json must contain a JSON object: {path}")
    return parse_list_payload(payload, list_name=list_name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import NYT bestseller popularity signals (separate from core books)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max list entries to process across all lists (smoke: 3).",
    )
    parser.add_argument(
        "--lists",
        default=",".join(DEFAULT_LISTS),
        help="Comma-separated NYT list name encodings (default: hardcover-fiction).",
    )
    parser.add_argument(
        "--list-date",
        default="current",
        help="List date YYYY-MM-DD or 'current' (default: current).",
    )
    parser.add_argument(
        "--books-csv",
        type=Path,
        default=None,
        help="Catalog CSV for matching (default: books_enriched.csv or books_clean.csv).",
    )
    parser.add_argument(
        "--from-json",
        type=Path,
        default=None,
        help="Optional cached NYT list JSON (skips live API).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROCESSED_DIR / "popularity_signals_report.json",
        help="Review report JSON path.",
    )
    parser.add_argument(
        "--cache-raw",
        action="store_true",
        help="Write fetched NYT payloads under data/raw/ (gitignored).",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Sleep between NYT list requests (default: 12 for rate limits).",
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Upsert strong/medium matches into public.book_popularity_signals.",
    )
    args = parser.parse_args()

    list_names = [part.strip() for part in args.lists.split(",") if part.strip()]
    if not list_names:
        raise SystemExit("No list names provided.")

    books_csv = resolve_books_csv(args.books_csv)
    catalog = load_catalog(books_csv)
    isbn_index = build_isbn_index(catalog)
    title_author_index = build_title_author_index(catalog)
    title_index = build_title_index(catalog)

    stats = ImportStats()
    matched_rows: list[dict[str, Any]] = []
    weak_rows: list[dict[str, Any]] = []
    unmatched_rows: list[dict[str, Any]] = []
    db_rows: list[dict[str, Any]] = []

    api_key: str | None = None
    if args.from_json is None:
        api_key = get_api_key()

    remaining = args.limit
    for index, list_name in enumerate(list_names):
        if remaining is not None and remaining <= 0:
            break

        if args.from_json is not None:
            if index > 0:
                break
            entries = load_entries_from_json(args.from_json, list_name=list_name)
            stats.lists_fetched += 1
        else:
            assert api_key is not None
            if index > 0:
                time.sleep(args.sleep_seconds)
            try:
                payload = fetch_nyt_list(
                    api_key,
                    list_name,
                    list_date=args.list_date,
                    sleep_seconds=args.sleep_seconds,
                )
            except RuntimeError:
                stats.api_errors += 1
                raise
            stats.lists_fetched += 1
            if args.cache_raw:
                RAW_DIR.mkdir(parents=True, exist_ok=True)
                cache_path = RAW_DIR / f"nyt_{list_name}_{args.list_date}.json"
                cache_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            entries = parse_list_payload(payload, list_name=list_name)

        for entry in entries:
            if remaining is not None and remaining <= 0:
                break
            stats.entries_seen += 1
            if remaining is not None:
                remaining -= 1

            result = match_entry(
                entry,
                isbn_index=isbn_index,
                title_author_index=title_author_index,
                title_index=title_index,
            )
            base = {
                "list_name": entry.list_name,
                "published_at": entry.published_at.isoformat() if entry.published_at else None,
                "rank": entry.rank,
                "title": entry.title,
                "author": entry.author,
                "isbns": entry.isbns,
                "provider_id": entry.provider_id,
            }

            if result.status == "matched" and result.book_id and result.strength in {
                "strong",
                "medium",
            }:
                if result.strength == "strong":
                    stats.matched_strong += 1
                else:
                    stats.matched_medium += 1
                row = {
                    **base,
                    "status": "matched",
                    "strength": result.strength,
                    "book_id": result.book_id,
                    "matched_on": result.matched_on,
                    "catalog_title": result.catalog_title,
                    "catalog_author": result.catalog_author,
                }
                matched_rows.append(row)
                db_rows.append(
                    {
                        "book_id": result.book_id,
                        "provider": PROVIDER,
                        "provider_id": entry.provider_id,
                        "list_name": entry.list_name,
                        "rank": entry.rank,
                        "published_at": entry.published_at,
                        "matched_on": result.matched_on,
                        "raw_payload": Json(entry.raw),
                    }
                )
            elif result.status == "weak":
                stats.weak += 1
                weak_rows.append(
                    {
                        **base,
                        "status": "weak",
                        "strength": "weak",
                        "book_id": result.book_id,
                        "matched_on": result.matched_on,
                        "catalog_title": result.catalog_title,
                        "catalog_author": result.catalog_author,
                    }
                )
            else:
                stats.unmatched += 1
                unmatched_rows.append({**base, "status": "unmatched"})

    write_report(
        args.report,
        stats=stats,
        matched=matched_rows,
        weak=weak_rows,
        unmatched=unmatched_rows,
        meta={
            "provider": PROVIDER,
            "lists": list_names,
            "list_date": args.list_date,
            "books_csv": str(books_csv),
            "from_json": str(args.from_json) if args.from_json else None,
            "write_db": args.write_db,
            "limit": args.limit,
        },
    )

    if args.write_db:
        # Partial unique index needs provider_id; published_at needed for stable conflict key.
        writable = [
            row
            for row in db_rows
            if row.get("provider_id") and row.get("published_at") is not None
        ]
        skipped = len(db_rows) - len(writable)
        stats.written = write_db_rows(writable, get_database_url())
        if skipped:
            print(
                f"Skipped {skipped} matched rows missing provider_id or published_at "
                "(no DB upsert)."
            )

    print(
        "Popularity import complete: "
        f"lists={stats.lists_fetched} seen={stats.entries_seen} "
        f"strong={stats.matched_strong} medium={stats.matched_medium} "
        f"weak={stats.weak} unmatched={stats.unmatched} "
        f"written={stats.written}"
    )
    print(f"Report: {args.report}")
    print(f"Report text: {args.report.with_suffix('.txt')}")
    if not args.write_db:
        print("DB write skipped (pass --write-db after applying the migration).")


if __name__ == "__main__":
    main()
