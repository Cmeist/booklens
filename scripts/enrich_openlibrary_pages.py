"""Fill missing page_count from Open Library edition data.

Uses work editions' number_of_pages. Prefer median of positive page counts.
"""

from __future__ import annotations

import argparse
import os
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"


@dataclass
class PagesStats:
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


def nullable_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def has_page_count(row: dict[str, Any]) -> bool:
    return nullable_int(row.get("page_count")) is not None


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


def fetch_edition_page_counts(
    work_key: str,
    *,
    headers: dict[str, str],
    sleep_seconds: float,
    max_attempts: int = 3,
) -> list[int]:
    url = f"https://openlibrary.org{work_key}/editions.json?limit=50"
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            payload = response.json()
            entries = payload.get("entries") or []
            pages: list[int] = []
            for entry in entries:
                count = nullable_int(entry.get("number_of_pages"))
                if count is not None:
                    pages.append(count)
            return pages
        except requests.RequestException as exc:
            if attempt == max_attempts:
                raise RuntimeError(f"Open Library editions request failed: {exc}") from exc
            time.sleep(sleep_seconds * attempt)
    return []


def choose_page_count(pages: list[int]) -> int | None:
    if not pages:
        return None
    filtered = [p for p in pages if 40 <= p <= 2000]
    pool = filtered or pages
    return int(statistics.median(pool))


def write_report(
    stats: PagesStats,
    out_path: Path,
    *,
    input_path: Path,
    output_path: Path,
) -> None:
    lines = [
        "BookLens Open Library Pages Enrichment Report",
        "=============================================",
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


def sync_page_counts_to_sibling(output_df: pd.DataFrame, output_path: Path) -> None:
    sibling = (
        PROCESSED_DIR / "books_clean.csv"
        if output_path.name != "books_clean.csv"
        else PROCESSED_DIR / "books_enriched.csv"
    )
    if not sibling.exists() or sibling.resolve() == output_path.resolve():
        return
    if "id" not in output_df.columns:
        return

    sibling_df = pd.read_csv(sibling)
    if "id" not in sibling_df.columns:
        return
    if "page_count" not in sibling_df.columns:
        sibling_df["page_count"] = pd.NA

    page_map = output_df.set_index("id")["page_count"]
    sibling_df = sibling_df.set_index("id")
    missing = sibling_df["page_count"].isna() | (sibling_df["page_count"].astype(str) == "")
    updates = page_map.reindex(sibling_df.index)
    sibling_df.loc[missing, "page_count"] = updates[missing]
    sibling_df = sibling_df.reset_index()
    sibling_df.to_csv(sibling, index=False)
    # Keep enriched preferred by seed_supabase mtime rule when we just bumped clean.
    if sibling.name == "books_clean.csv" and output_path.exists():
        os.utime(output_path, None)


def enrich_openlibrary_pages(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    *,
    contact: str,
    limit: int | None,
    sleep_seconds: float,
) -> PagesStats:
    headers = {
        "User-Agent": f"BookLensPagesEnricher/0.1 (contact: {contact})",
        "Accept": "application/json",
    }

    df = pd.read_csv(input_path)
    rows = df.to_dict(orient="records")
    rows_to_enrich = rows[:limit] if limit is not None else rows

    stats = PagesStats()
    enriched_rows: list[dict[str, Any]] = []

    for record in rows_to_enrich:
        row = dict(record)
        stats.searched += 1
        title = str(row.get("title") or "unknown title")

        if has_page_count(row):
            stats.already_present += 1
            enriched_rows.append(row)
            continue

        work_key = normalize_work_key(row.get("source_id"))
        if not work_key:
            stats.missing += 1
            enriched_rows.append(row)
            continue

        try:
            pages = fetch_edition_page_counts(
                work_key,
                headers=headers,
                sleep_seconds=sleep_seconds,
            )
            time.sleep(sleep_seconds)
            page_count = choose_page_count(pages)
        except RuntimeError:
            stats.api_errors += 1
            enriched_rows.append(row)
            continue

        if page_count is None:
            stats.missing += 1
            enriched_rows.append(row)
            continue

        row["page_count"] = page_count
        stats.filled += 1
        if len(stats.samples) < 15:
            stats.samples.append(f"{title}: {page_count} pages")
        enriched_rows.append(row)

    if limit is not None:
        enriched_rows.extend(dict(record) for record in rows[limit:])

    output_df = pd.DataFrame(enriched_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)
    sync_page_counts_to_sibling(output_df, output_path)
    write_report(stats, report_path, input_path=input_path, output_path=output_path)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fill missing page_count from Open Library editions."
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
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROCESSED_DIR / "openlibrary_pages_report.txt",
    )
    parser.add_argument("--contact", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    args = parser.parse_args()

    try:
        contact = resolve_contact(args.contact)
    except ValueError as exc:
        parser.error(str(exc))

    if not args.input.exists():
        parser.error(f"Input CSV not found: {args.input}")

    stats = enrich_openlibrary_pages(
        input_path=args.input,
        output_path=args.output,
        report_path=args.report,
        contact=contact,
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
    )
    print(
        f"Open Library pages: filled {stats.filled}, "
        f"already present {stats.already_present}, "
        f"missing {stats.missing}, api errors {stats.api_errors}"
    )


if __name__ == "__main__":
    main()
