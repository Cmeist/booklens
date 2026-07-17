"""
Enrich processed BookLens books with Google Books metadata.

Reads books_clean.csv, fills missing fields only, and writes books_enriched.csv
for seed_supabase.py. Requires a server-only GOOGLE_BOOKS_API_KEY in .env.

Examples:
    uv run python scripts/enrich_google_books.py
    uv run python scripts/enrich_google_books.py --limit 3
    uv run python scripts/enrich_google_books.py --input data/processed/books_clean.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests
from dotenv import load_dotenv

try:
    from scripts.tag_normalization import normalize_tags, split_source_tags, tags_to_string
except ModuleNotFoundError:  # Direct execution: python scripts/enrich_google_books.py
    from tag_normalization import normalize_tags, split_source_tags, tags_to_string

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"
CURRENT_YEAR = 2026


@dataclass
class EnrichmentStats:
    searched: int = 0
    matched: int = 0
    skipped_weak: int = 0
    unmatched: int = 0
    api_errors: int = 0
    fields_improved: dict[str, int] = field(
        default_factory=lambda: {
            "page_count": 0,
            "cover_url": 0,
            "description": 0,
            "publication_year": 0,
            "tags": 0,
            "average_rating": 0,
            "rating_count": 0,
        }
    )
    isbns_added: int = 0
    weak_matches: list[str] = field(default_factory=list)
    unmatched_titles: list[str] = field(default_factory=list)
    unmapped_tags: Counter[str] = field(default_factory=Counter)
    unmapped_tag_samples: dict[str, list[str]] = field(default_factory=dict)


def get_api_key() -> str:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("GOOGLE_BOOKS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GOOGLE_BOOKS_API_KEY is required. "
            "Set it in .env as a server-only variable."
        )
    return api_key


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
    return author.split(";")[0].strip()


def parse_tags(value: Any) -> list[str]:
    return split_source_tags(value)


def parse_isbns_column(value: Any) -> list[dict[str, str | None]]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    return []


def isbns_to_json(isbns: list[dict[str, str | None]]) -> str:
    return json.dumps(isbns, separators=(",", ":"))


def extra_sources_to_json(sources: list[dict[str, str | None]]) -> str:
    return json.dumps(sources, separators=(",", ":"))


def parse_publication_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(\d{4})", value)
    if not match:
        return None
    year = int(match.group(1))
    if year < 1400 or year > CURRENT_YEAR:
        return None
    return year


def to_decade(year: int | None) -> str | None:
    if year is None:
        return None
    decade_start = year // 10 * 10
    return f"{decade_start}s"


def is_missing_int(value: Any) -> bool:
    return nullable_int(value) is None


def is_missing_text(value: Any) -> bool:
    return nullable_text(value) is None


def nullable_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0 or number > 5:
        return None
    return number


def should_replace_ratings(
    existing_average: Any,
    existing_count: Any,
    candidate_average: float,
    candidate_count: int,
) -> bool:
    """Keep the rating pair with the higher rating_count (merge rule)."""
    current_count = nullable_int(existing_count)
    current_average = nullable_float(existing_average)
    if current_count is None or current_average is None or current_count <= 0:
        return True
    return candidate_count > current_count


def https_cover_url(volume_info: dict[str, Any]) -> str | None:
    links = volume_info.get("imageLinks") or {}
    for key in ("extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail"):
        url = nullable_text(links.get(key))
        if url:
            return url.replace("http://", "https://", 1)
    return None


def volume_isbns(volume_info: dict[str, Any]) -> list[dict[str, str | None]]:
    records: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for identifier in volume_info.get("industryIdentifiers") or []:
        raw_type = nullable_text(identifier.get("type"))
        raw_value = nullable_text(identifier.get("identifier"))
        if not raw_value:
            continue
        isbn = normalize_isbn(raw_value)
        if not isbn or isbn in seen:
            continue
        seen.add(isbn)
        records.append(
            {
                "isbn": isbn,
                "isbnType": raw_type,
                "provider": "googlebooks",
            }
        )
    return records


def volume_contains_isbn(volume_info: dict[str, Any], target_isbn: str) -> bool:
    for record in volume_isbns(volume_info):
        if record["isbn"] == target_isbn:
            return True
    return False


def titles_match(book_title: str, volume_title: str | None) -> bool:
    if not volume_title:
        return False
    return normalize_key(book_title) == normalize_key(volume_title)


def authors_match(book_author: str, volume_authors: list[str] | None) -> bool:
    book_author_norm = normalize_key(first_author(book_author))
    if not book_author_norm:
        return False
    for volume_author in volume_authors or []:
        if normalize_key(volume_author) == book_author_norm:
            return True
    return False


def fetch_volumes(
    api_key: str,
    query: str,
    *,
    max_attempts: int = 3,
    sleep_seconds: float = 0.25,
) -> list[dict[str, Any]]:
    url = f"{GOOGLE_BOOKS_API}?q={quote(query)}&maxResults=5&key={api_key}"
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            payload = response.json()
            return payload.get("items") or []
        except requests.RequestException as exc:
            if attempt == max_attempts:
                raise RuntimeError(f"Google Books request failed: {exc}") from exc
            time.sleep(sleep_seconds * attempt)
    return []


def choose_volume_by_isbn(
    items: list[dict[str, Any]],
    isbn: str,
) -> dict[str, Any] | None:
    for item in items:
        volume_info = item.get("volumeInfo") or {}
        if volume_contains_isbn(volume_info, isbn):
            return item
    return None


def choose_volume_by_title_author(
    items: list[dict[str, Any]],
    title: str,
    author: str,
) -> tuple[dict[str, Any] | None, str]:
    saw_weak = False
    for item in items:
        volume_info = item.get("volumeInfo") or {}
        volume_title = nullable_text(volume_info.get("title"))
        volume_authors = volume_info.get("authors") or []

        if titles_match(title, volume_title or "") and authors_match(author, volume_authors):
            return item, "strong"

        if titles_match(title, volume_title or "") and not authors_match(author, volume_authors):
            saw_weak = True

    if saw_weak:
        return None, "weak"
    return None, "none"


def find_google_volume(
    api_key: str,
    row: dict[str, Any],
    *,
    sleep_seconds: float,
) -> tuple[dict[str, Any] | None, str]:
    title = nullable_text(row.get("title")) or ""
    author = nullable_text(row.get("author")) or ""

    existing_isbns = parse_isbns_column(row.get("isbns"))
    for isbn_record in existing_isbns:
        isbn = normalize_isbn(isbn_record.get("isbn") or "")
        if not isbn:
            continue
        items = fetch_volumes(api_key, f"isbn:{isbn}", sleep_seconds=sleep_seconds)
        time.sleep(sleep_seconds)
        match = choose_volume_by_isbn(items, isbn)
        if match:
            return match, "isbn"

    first = first_author(author)
    if not title or not first:
        return None, "none"

    query = f'intitle:"{title}" inauthor:"{first}"'
    items = fetch_volumes(api_key, query, sleep_seconds=sleep_seconds)
    time.sleep(sleep_seconds)
    return choose_volume_by_title_author(items, title, author)


def merge_tags(existing_tags: list[str], categories: list[str] | None) -> list[str]:
    merged = list(existing_tags)
    seen = set(existing_tags)
    for category in categories or []:
        tag = category.strip().lower()
        tag = re.sub(r"[_-]+", " ", tag)
        tag = re.sub(r"\s+", " ", tag).strip()
        if tag and tag not in seen:
            merged.append(tag)
            seen.add(tag)
    return merged


def enrich_row(
    row: dict[str, Any],
    volume: dict[str, Any],
    stats: EnrichmentStats,
) -> dict[str, Any]:
    enriched = dict(row)
    volume_info = volume.get("volumeInfo") or {}
    volume_id = nullable_text(volume.get("id"))

    if is_missing_int(enriched.get("page_count")):
        page_count = nullable_int(volume_info.get("pageCount"))
        if page_count and page_count > 0:
            enriched["page_count"] = page_count
            stats.fields_improved["page_count"] += 1

    if is_missing_text(enriched.get("cover_url")):
        cover_url = https_cover_url(volume_info)
        if cover_url:
            enriched["cover_url"] = cover_url
            stats.fields_improved["cover_url"] += 1

    if not nullable_text(enriched.get("description")):
        description = nullable_text(volume_info.get("description"))
        if description:
            enriched["description"] = description
            stats.fields_improved["description"] += 1

    if is_missing_int(enriched.get("publication_year")):
        year = parse_publication_year(nullable_text(volume_info.get("publishedDate")))
        if year is not None:
            enriched["publication_year"] = year
            enriched["decade"] = to_decade(year)
            stats.fields_improved["publication_year"] += 1

    previous_tags = tags_to_string(normalize_tags(enriched.get("tags")).tags)
    existing_tags = parse_tags(enriched.get("tags"))
    merged_tags = merge_tags(existing_tags, volume_info.get("categories"))
    tag_result = normalize_tags(merged_tags)
    normalized_tags = tags_to_string(tag_result.tags)
    enriched["tags"] = normalized_tags
    if normalized_tags != previous_tags:
        stats.fields_improved["tags"] += 1
    title = nullable_text(enriched.get("title")) or "unknown title"
    for tag in tag_result.unmapped:
        stats.unmapped_tags[tag] += 1
        samples = stats.unmapped_tag_samples.setdefault(tag, [])
        if len(samples) < 3 and title not in samples:
            samples.append(title)

    google_average = nullable_float(volume_info.get("averageRating"))
    google_count = nullable_int(volume_info.get("ratingsCount"))
    if (
        google_average is not None
        and google_count is not None
        and google_count > 0
        and should_replace_ratings(
            enriched.get("average_rating"),
            enriched.get("rating_count"),
            google_average,
            google_count,
        )
    ):
        enriched["average_rating"] = round(google_average, 2)
        enriched["rating_count"] = google_count
        stats.fields_improved["average_rating"] += 1
        stats.fields_improved["rating_count"] += 1

    isbn_records = parse_isbns_column(enriched.get("isbns"))
    known_isbns = {normalize_isbn(record.get("isbn") or "") for record in isbn_records}
    for record in volume_isbns(volume_info):
        isbn = record.get("isbn")
        if not isbn or isbn in known_isbns:
            continue
        isbn_records.append(record)
        known_isbns.add(isbn)
        stats.isbns_added += 1
    enriched["isbns"] = isbns_to_json(isbn_records)

    if volume_id:
        extra_sources = []
        raw_extra = enriched.get("extra_sources")
        if isinstance(raw_extra, str) and raw_extra.strip():
            try:
                parsed_extra = json.loads(raw_extra)
                if isinstance(parsed_extra, list):
                    extra_sources = [item for item in parsed_extra if isinstance(item, dict)]
            except json.JSONDecodeError:
                extra_sources = []
        extra_sources = [
            item
            for item in extra_sources
            if not (
                item.get("provider") == "googlebooks"
                and item.get("provider_id") == volume_id
            )
        ]
        extra_sources.append(
            {
                "provider": "googlebooks",
                "provider_id": volume_id,
                "provider_url": f"https://books.google.com/books?id={volume_id}",
            }
        )
        enriched["extra_sources"] = extra_sources_to_json(extra_sources)

    return enriched


def write_report(stats: EnrichmentStats, out_path: Path, *, input_path: Path, output_path: Path) -> None:
    lines = [
        "BookLens Google Books Enrichment Report",
        "=======================================",
        f"Input: {input_path}",
        f"Output: {output_path}",
        "",
        f"Searched: {stats.searched}",
        f"Matched: {stats.matched}",
        f"Skipped weak matches: {stats.skipped_weak}",
        f"Unmatched: {stats.unmatched}",
        f"API errors: {stats.api_errors}",
        "",
        "Fields improved:",
        f"- page_count: {stats.fields_improved['page_count']}",
        f"- cover_url: {stats.fields_improved['cover_url']}",
        f"- description: {stats.fields_improved['description']}",
        f"- publication_year: {stats.fields_improved['publication_year']}",
        f"- tags: {stats.fields_improved['tags']}",
        f"- average_rating: {stats.fields_improved['average_rating']}",
        f"- rating_count: {stats.fields_improved['rating_count']}",
        f"- isbns added: {stats.isbns_added}",
        f"- unmapped tag assignments: {sum(stats.unmapped_tags.values())}",
        "",
    ]

    if stats.weak_matches:
        lines.append("Weak matches skipped:")
        for item in stats.weak_matches[:20]:
            lines.append(f"- {item}")
        lines.append("")

    if stats.unmatched_titles:
        lines.append("Unmatched books:")
        for item in stats.unmatched_titles[:20]:
            lines.append(f"- {item}")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_unmapped_tags_report(stats: EnrichmentStats, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["tag", "occurrence_count", "sample_books"],
        )
        writer.writeheader()
        for tag, count in stats.unmapped_tags.most_common():
            writer.writerow(
                {
                    "tag": tag,
                    "occurrence_count": count,
                    "sample_books": " | ".join(stats.unmapped_tag_samples.get(tag, [])),
                }
            )


def enrich_books(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    *,
    limit: int | None,
    sleep_seconds: float,
) -> EnrichmentStats:
    api_key = get_api_key()
    df = pd.read_csv(input_path)
    rows = df.to_dict(orient="records")
    rows_to_enrich = rows[:limit] if limit is not None else rows

    stats = EnrichmentStats()
    enriched_rows: list[dict[str, Any]] = []

    for record in rows_to_enrich:
        row = dict(record)
        if "isbns" not in row or pd.isna(row.get("isbns")):
            row["isbns"] = "[]"
        if "extra_sources" not in row or pd.isna(row.get("extra_sources")):
            row["extra_sources"] = "[]"

        stats.searched += 1
        title = nullable_text(row.get("title")) or "unknown title"

        try:
            volume, match_kind = find_google_volume(api_key, row, sleep_seconds=sleep_seconds)
        except RuntimeError:
            stats.api_errors += 1
            enriched_rows.append(row)
            continue

        if match_kind == "weak":
            stats.skipped_weak += 1
            stats.weak_matches.append(title)
            enriched_rows.append(row)
            continue

        if volume is None:
            stats.unmatched += 1
            stats.unmatched_titles.append(title)
            enriched_rows.append(row)
            continue

        stats.matched += 1
        enriched_rows.append(enrich_row(row, volume, stats))

    if limit is not None:
        for record in rows[limit:]:
            row = dict(record)
            if "isbns" not in row or pd.isna(row.get("isbns")):
                row["isbns"] = "[]"
            if "extra_sources" not in row or pd.isna(row.get("extra_sources")):
                row["extra_sources"] = "[]"
            enriched_rows.append(row)

    for row in enriched_rows:
        row["tags"] = tags_to_string(normalize_tags(row.get("tags")).tags)

    output_df = pd.DataFrame(enriched_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)
    write_report(stats, report_path, input_path=input_path, output_path=output_path)
    write_unmapped_tags_report(
        stats,
        report_path.with_name("google_books_unmapped_tags.csv"),
    )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich BookLens books with Google Books metadata.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROCESSED_DIR / "books_clean.csv",
        help="Processed books CSV to enrich.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROCESSED_DIR / "books_enriched.csv",
        help="Enriched books CSV for seed_supabase.py.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROCESSED_DIR / "google_books_enrichment_report.txt",
        help="Enrichment summary report path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N rows (useful for smoke tests).",
    )
    parser.add_argument("--sleep-seconds", type=float, default=0.25)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    stats = enrich_books(
        args.input,
        args.output,
        args.report,
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
    )

    print(f"Wrote {args.output}")
    print(f"Wrote {args.report}")
    print(
        "Enrichment summary: "
        f"searched={stats.searched}, matched={stats.matched}, "
        f"skipped_weak={stats.skipped_weak}, unmatched={stats.unmatched}, "
        f"isbns_added={stats.isbns_added}"
    )


if __name__ == "__main__":
    main()
