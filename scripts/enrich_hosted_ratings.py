"""Fill missing hosted book rating aggregates (Open Library, then Google Books).

Ratings-only: UPDATE average_rating / rating_count. Never touches tags,
recommendations, or other book columns. Default is dry-run; pass --apply to write.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import psycopg
from dotenv import load_dotenv

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from enrich_google_books import (  # noqa: E402
    find_google_volume,
    get_api_key,
    nullable_float as google_nullable_float,
    nullable_int as google_nullable_int,
    should_replace_ratings,
)
from enrich_openlibrary_ratings import (  # noqa: E402
    fetch_work_ratings,
    has_ratings,
    normalize_work_key,
    resolve_contact,
)
from seed_supabase import get_database_url  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"
DEFAULT_REPORT = PROCESSED_DIR / "hosted_ratings_fill_report.txt"
EXPECTED_PROJECT_REF = "ickeyhuybqtpzdwypzsn"

MISSING_BOOKS_SQL = """
select b.id,
       b.title,
       b.author,
       b.source,
       b.source_id,
       b.average_rating,
       b.rating_count,
       coalesce(
         array_agg(i.isbn) filter (where i.isbn is not null),
         '{}'
       ) as isbns
from public.books b
left join public.book_isbns i on i.book_id = b.id
where b.average_rating is null
   or b.rating_count is null
   or b.rating_count = 0
group by b.id
order by b.title, b.id
"""

COVERAGE_SQL = """
select count(*)::int as books,
       count(*) filter (
         where average_rating is not null
           and rating_count is not null
           and rating_count > 0
       )::int as rated,
       count(*) filter (
         where average_rating is null
            or rating_count is null
            or rating_count = 0
       )::int as missing
from public.books
"""

CHURN_SQL = """
select (select count(*)::int from public.book_tags) as tags,
       (select count(*)::int from public.book_recommendations) as recs
"""

APPLY_UPDATE_SQL = """
update public.books
set average_rating = %s,
    rating_count = %s,
    updated_at = now()
where id = %s
  and (
    average_rating is null
    or rating_count is null
    or rating_count = 0
  )
"""


@dataclass
class FillStats:
    searched: int = 0
    ol_filled: int = 0
    google_filled: int = 0
    still_missing: int = 0
    api_errors: int = 0
    applied: int = 0
    samples: list[str] = field(default_factory=list)
    remaining: list[str] = field(default_factory=list)


def assert_booklens_database(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = parsed.hostname or ""
    user = unquote(parsed.username or "")
    if EXPECTED_PROJECT_REF in host or EXPECTED_PROJECT_REF in user or EXPECTED_PROJECT_REF in database_url:
        return host or "unknown-host"
    raise RuntimeError(
        f"SUPABASE_DB_URL does not identify BookLens project {EXPECTED_PROJECT_REF}. "
        f"Host={host!r}. Refusing to continue."
    )


def fetch_coverage(conn: psycopg.Connection) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute(COVERAGE_SQL)
        books, rated, missing = cur.fetchone()
        return {"books": books, "rated": rated, "missing": missing}


def fetch_churn(conn: psycopg.Connection) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute(CHURN_SQL)
        tags, recs = cur.fetchone()
        return {"tags": tags, "recs": recs}


def fetch_missing_books(conn: psycopg.Connection, limit: int | None) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(MISSING_BOOKS_SQL)
        columns = [desc.name for desc in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    if limit is not None:
        return rows[:limit]
    return rows


def isbns_for_google(row: dict[str, Any]) -> str:
    raw = row.get("isbns") or []
    records = [{"isbn": str(isbn), "isbnType": None} for isbn in raw if isbn]
    return json.dumps(records, separators=(",", ":"))


def google_ratings_for_row(
    api_key: str,
    row: dict[str, Any],
    *,
    sleep_seconds: float,
) -> tuple[float | None, int | None]:
    lookup_row = {
        "title": row.get("title"),
        "author": row.get("author"),
        "isbns": isbns_for_google(row),
        "average_rating": row.get("average_rating"),
        "rating_count": row.get("rating_count"),
    }
    volume, _match_kind = find_google_volume(api_key, lookup_row, sleep_seconds=sleep_seconds)
    if not volume:
        return None, None
    volume_info = volume.get("volumeInfo") or {}
    average = google_nullable_float(volume_info.get("averageRating"))
    count = google_nullable_int(volume_info.get("ratingsCount"))
    if average is None or count is None or count <= 0:
        return None, None
    if not should_replace_ratings(
        lookup_row.get("average_rating"),
        lookup_row.get("rating_count"),
        average,
        count,
    ):
        return None, None
    return round(average, 2), count


def write_report(
    report_path: Path,
    *,
    apply: bool,
    skip_google: bool,
    limit: int | None,
    host: str,
    baseline: dict[str, int],
    churn_before: dict[str, int],
    churn_after: dict[str, int] | None,
    final_coverage: dict[str, int] | None,
    stats: FillStats,
) -> None:
    lines = [
        "BookLens Hosted Ratings Fill Report",
        "===================================",
        f"Mode: {'APPLY' if apply else 'DRY-RUN'}",
        f"Skip Google: {skip_google}",
        f"Limit: {limit if limit is not None else 'none'}",
        f"DB host: {host}",
        f"Expected project ref: {EXPECTED_PROJECT_REF}",
        "",
        "Baseline coverage:",
        f"- books: {baseline['books']}",
        f"- rated: {baseline['rated']}",
        f"- missing: {baseline['missing']}",
        "",
        "Churn baseline:",
        f"- book_tags: {churn_before['tags']}",
        f"- book_recommendations: {churn_before['recs']}",
        "",
        f"Searched: {stats.searched}",
        f"Filled via Open Library: {stats.ol_filled}",
        f"Filled via Google Books: {stats.google_filled}",
        f"Still missing: {stats.still_missing}",
        f"API errors: {stats.api_errors}",
        f"Applied updates: {stats.applied}",
        "",
    ]
    if final_coverage is not None:
        lines.extend(
            [
                "Final coverage:",
                f"- books: {final_coverage['books']}",
                f"- rated: {final_coverage['rated']}",
                f"- missing: {final_coverage['missing']}",
                "",
            ]
        )
    if churn_after is not None:
        lines.extend(
            [
                "Churn after:",
                f"- book_tags: {churn_after['tags']}",
                f"- book_recommendations: {churn_after['recs']}",
                f"- tags_unchanged: {churn_after['tags'] == churn_before['tags']}",
                f"- recs_unchanged: {churn_after['recs'] == churn_before['recs']}",
                "",
            ]
        )
    if stats.samples:
        lines.append("Sample fills:")
        for item in stats.samples[:20]:
            lines.append(f"- {item}")
        lines.append("")
    if stats.remaining:
        lines.append("Remaining missing (up to 40):")
        for item in stats.remaining[:40]:
            lines.append(f"- {item}")
        lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run(
    *,
    apply: bool,
    limit: int | None,
    contact: str,
    sleep_seconds: float,
    skip_google: bool,
    report_path: Path,
) -> FillStats:
    database_url = get_database_url()
    host = assert_booklens_database(database_url)
    ol_headers = {
        "User-Agent": f"BookLensHostedRatingsFill/0.1 (contact: {contact})",
        "Accept": "application/json",
    }
    google_key: str | None = None
    if not skip_google:
        google_key = get_api_key()

    stats = FillStats()
    candidates: list[tuple[str, float, int, str]] = []

    with psycopg.connect(database_url) as conn:
        baseline = fetch_coverage(conn)
        churn_before = fetch_churn(conn)
        rows = fetch_missing_books(conn, limit)

        for row in rows:
            stats.searched += 1
            book_id = str(row["id"])
            title = str(row.get("title") or "unknown title")
            average: float | None = None
            count: int | None = None
            source = ""

            if has_ratings(row):
                stats.still_missing += 1
                continue

            work_key = normalize_work_key(row.get("source_id"))
            if work_key:
                try:
                    average, count = fetch_work_ratings(
                        work_key,
                        headers=ol_headers,
                        sleep_seconds=sleep_seconds,
                    )
                    time.sleep(sleep_seconds)
                except RuntimeError:
                    stats.api_errors += 1
                    average, count = None, None

            if average is not None and count is not None and count > 0:
                source = "openlibrary"
                stats.ol_filled += 1
            elif google_key is not None:
                try:
                    average, count = google_ratings_for_row(
                        google_key,
                        row,
                        sleep_seconds=sleep_seconds,
                    )
                except RuntimeError:
                    stats.api_errors += 1
                    average, count = None, None
                if average is not None and count is not None and count > 0:
                    source = "google"
                    stats.google_filled += 1

            if average is None or count is None or count <= 0:
                stats.still_missing += 1
                if len(stats.remaining) < 40:
                    stats.remaining.append(f"{title} ({book_id})")
                continue

            candidates.append((book_id, average, count, source))
            if len(stats.samples) < 20:
                stats.samples.append(f"{title}: {average} ({count}) via {source}")

        churn_after: dict[str, int] | None = None
        final_coverage: dict[str, int] | None = None

        if apply and candidates:
            with conn.cursor() as cur:
                for book_id, average, count, _source in candidates:
                    cur.execute(APPLY_UPDATE_SQL, (average, count, book_id))
                    stats.applied += cur.rowcount
            conn.commit()
            final_coverage = fetch_coverage(conn)
            churn_after = fetch_churn(conn)
            if (
                churn_after["tags"] != churn_before["tags"]
                or churn_after["recs"] != churn_before["recs"]
            ):
                raise RuntimeError(
                    "Tag or recommendation counts changed during ratings fill; aborting handoff."
                )
        elif apply:
            final_coverage = baseline
            churn_after = churn_before

        write_report(
            report_path,
            apply=apply,
            skip_google=skip_google,
            limit=limit,
            host=host,
            baseline=baseline,
            churn_before=churn_before,
            churn_after=churn_after,
            final_coverage=final_coverage,
            stats=stats,
        )

    return stats


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Fill missing hosted BookLens rating aggregates (dry-run by default)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write rating updates to Supabase. Default is dry-run.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max missing books to process.")
    parser.add_argument(
        "--contact",
        default=None,
        help="Contact email for Open Library User-Agent (or BOOKLENS_CONTACT_EMAIL).",
    )
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument(
        "--skip-google",
        action="store_true",
        help="Only use Open Library; skip Google Books secondary pass.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Report path (default: {DEFAULT_REPORT})",
    )
    args = parser.parse_args()

    contact = resolve_contact(args.contact)
    stats = run(
        apply=args.apply,
        limit=args.limit,
        contact=contact,
        sleep_seconds=args.sleep_seconds,
        skip_google=args.skip_google,
        report_path=args.report,
    )
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(
        f"[{mode}] searched={stats.searched} ol={stats.ol_filled} "
        f"google={stats.google_filled} missing={stats.still_missing} "
        f"errors={stats.api_errors} applied={stats.applied}"
    )
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
