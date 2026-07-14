"""Enrich BookLens books with Open Library community ratings.

Primary ratings source. Matches on existing Open Library work ids
(`source_id` like `/works/OL…W`) via the Search API fields
`ratings_average` and `ratings_count`.
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
SEARCH_API = "https://openlibrary.org/search.json"


@dataclass
class RatingsStats:
    searched: int = 0
    filled: int = 0
    already_present: int = 0
    missing: int = 0
    api_errors: int = 0
    samples: list[str] = field(default_factory=list)


def resolve_contact(cli_contact: str | None) -> str:
    if cli_contact and cli_contact.strip():
        return cli_contact.strip()

    load_dotenv(ROOT / ".env")
    env_contact = os.getenv("BOOKLENS_CONTACT_EMAIL", "").strip()
    if env_contact:
        return env_contact

    raise ValueError(
        "Contact email is required. Pass --contact or set BOOKLENS_CONTACT_EMAIL in .env."
    )


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


def nullable_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return number


def has_ratings(row: dict[str, Any]) -> bool:
    average = nullable_float(row.get("average_rating"))
    count = nullable_int(row.get("rating_count"))
    return average is not None and count is not None and count > 0


def normalize_work_key(source_id: Any) -> str | None:
    if source_id is None or (isinstance(source_id, float) and pd.isna(source_id)):
        return None
    text = str(source_id).strip()
    if not text:
        return None
    if text.startswith("/works/"):
        return text
    if text.startswith("OL") and text.endswith("W"):
        return f"/works/{text}"
    return text if "/works/" in text else None


def fetch_work_ratings(
    work_key: str,
    *,
    headers: dict[str, str],
    sleep_seconds: float,
    max_attempts: int = 3,
) -> tuple[float | None, int | None]:
    query = quote(f"key:{work_key}")
    url = (
        f"{SEARCH_API}?q={query}"
        f"&fields=key,ratings_average,ratings_count&limit=1"
    )

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            docs = response.json().get("docs") or []
            if not docs:
                return None, None
            average = nullable_float(docs[0].get("ratings_average"))
            count = nullable_int(docs[0].get("ratings_count"))
            if average is None or count is None or count <= 0:
                return None, None
            return round(average, 2), count
        except requests.RequestException as exc:
            if attempt == max_attempts:
                raise RuntimeError(f"Open Library ratings request failed: {exc}") from exc
            time.sleep(sleep_seconds * attempt)

    return None, None


def write_report(
    stats: RatingsStats,
    out_path: Path,
    *,
    input_path: Path,
    output_path: Path,
) -> None:
    lines = [
        "BookLens Open Library Ratings Enrichment Report",
        "===============================================",
        f"Input: {input_path}",
        f"Output: {output_path}",
        "",
        f"Searched: {stats.searched}",
        f"Filled: {stats.filled}",
        f"Already present: {stats.already_present}",
        f"Missing after lookup: {stats.missing}",
        f"API errors: {stats.api_errors}",
        "",
    ]
    if stats.samples:
        lines.append("Sample fills:")
        for item in stats.samples[:15]:
            lines.append(f"- {item}")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def enrich_openlibrary_ratings(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    *,
    contact: str,
    limit: int | None,
    sleep_seconds: float,
    overwrite: bool,
) -> RatingsStats:
    headers = {
        "User-Agent": f"BookLensRatingsEnricher/0.1 (contact: {contact})",
        "Accept": "application/json",
    }

    df = pd.read_csv(input_path)
    rows = df.to_dict(orient="records")
    rows_to_enrich = rows[:limit] if limit is not None else rows

    stats = RatingsStats()
    enriched_rows: list[dict[str, Any]] = []

    for record in rows_to_enrich:
        row = dict(record)
        stats.searched += 1
        title = str(row.get("title") or "unknown title")

        if has_ratings(row) and not overwrite:
            stats.already_present += 1
            enriched_rows.append(row)
            continue

        work_key = normalize_work_key(row.get("source_id"))
        if not work_key:
            stats.missing += 1
            enriched_rows.append(row)
            continue

        try:
            average, count = fetch_work_ratings(
                work_key,
                headers=headers,
                sleep_seconds=sleep_seconds,
            )
            time.sleep(sleep_seconds)
        except RuntimeError:
            stats.api_errors += 1
            enriched_rows.append(row)
            continue

        if average is None or count is None:
            stats.missing += 1
            enriched_rows.append(row)
            continue

        row["average_rating"] = average
        row["rating_count"] = count
        stats.filled += 1
        if len(stats.samples) < 15:
            stats.samples.append(f"{title}: {average} ({count})")
        enriched_rows.append(row)

    if limit is not None:
        enriched_rows.extend(dict(record) for record in rows[limit:])

    output_df = pd.DataFrame(enriched_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)

    # Keep books_enriched in sync when present so seed_supabase picks up ratings.
    enriched_path = PROCESSED_DIR / "books_enriched.csv"
    if enriched_path.exists() and enriched_path.resolve() != output_path.resolve():
        enriched_df = pd.read_csv(enriched_path)
        if "id" in enriched_df.columns and "id" in output_df.columns:
            rating_map = output_df.set_index("id")[["average_rating", "rating_count"]]
            for column in ("average_rating", "rating_count"):
                if column not in enriched_df.columns:
                    enriched_df[column] = pd.NA
            enriched_df = enriched_df.set_index("id")
            enriched_df.update(rating_map)
            enriched_df = enriched_df.reset_index()
            enriched_df.to_csv(enriched_path, index=False)

    write_report(stats, report_path, input_path=input_path, output_path=output_path)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich BookLens books with Open Library community ratings."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROCESSED_DIR / "books_clean.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROCESSED_DIR / "books_clean.csv",
        help="Defaults to overwriting books_clean.csv in place.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROCESSED_DIR / "openlibrary_ratings_report.txt",
    )
    parser.add_argument("--contact", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing rating fields when Open Library has data.",
    )
    args = parser.parse_args()

    try:
        contact = resolve_contact(args.contact)
    except ValueError as exc:
        parser.error(str(exc))

    if not args.input.exists():
        parser.error(f"Input CSV not found: {args.input}")

    stats = enrich_openlibrary_ratings(
        input_path=args.input,
        output_path=args.output,
        report_path=args.report,
        contact=contact,
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
        overwrite=args.overwrite,
    )

    print(
        f"Open Library ratings: filled {stats.filled}, "
        f"already present {stats.already_present}, "
        f"missing {stats.missing}, api errors {stats.api_errors}"
    )


if __name__ == "__main__":
    main()
