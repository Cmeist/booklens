"""Audit, apply, or restore canonical tags in hosted BookLens Postgres.

Dry-run is the default.  ``--apply`` is required for any database mutation.
This script never inserts, updates, or deletes rows in ``public.books``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

try:
    from scripts.seed_supabase import get_database_url, recommendations_for_books
    from scripts.tag_normalization import (
        CANONICAL_TAG_SET,
        MAX_TAGS_PER_BOOK,
        normalize_tags,
    )
except ModuleNotFoundError:  # Direct execution: python scripts/cleanup_hosted_tags.py
    from seed_supabase import get_database_url, recommendations_for_books
    from tag_normalization import CANONICAL_TAG_SET, MAX_TAGS_PER_BOOK, normalize_tags


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_ROOT = ROOT / "data" / "processed" / "tag_cleanup"

BOOKS_QUERY = """
select
  b.id,
  b.title,
  b.author,
  b.description,
  b.decade,
  b.page_count,
  b.rating_count,
  b.average_rating,
  coalesce(
    array_agg(bt.tag order by bt.tag) filter (where bt.tag is not null),
    '{}'::text[]
  ) as tags
from public.books b
left join public.book_tags bt on bt.book_id = b.id
group by b.id
order by b.id
"""

TAGS_QUERY = """
select book_id, tag
from public.book_tags
order by book_id, tag
"""

RECOMMENDATIONS_QUERY = """
select book_id, similar_book_id, score::float8 as score, reasons
from public.book_recommendations
order by book_id, similar_book_id
"""

TAG_INSERT = "insert into public.book_tags (book_id, tag) values (%s, %s)"
RECOMMENDATION_INSERT = """
insert into public.book_recommendations (
  book_id,
  similar_book_id,
  score,
  reasons
) values (%s, %s, %s, %s)
"""


def utc_run_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def catalog_id_hash(book_ids: list[str]) -> str:
    payload = "\n".join(sorted(book_ids)).encode()
    return hashlib.sha256(payload).hexdigest()


def percentile(values: list[int], percent: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 1)


def load_snapshot(database_url: str) -> dict[str, list[dict[str, Any]]]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(BOOKS_QUERY)
            books = list(cur.fetchall())
            cur.execute(TAGS_QUERY)
            tags = list(cur.fetchall())
            cur.execute(RECOMMENDATIONS_QUERY)
            recommendations = list(cur.fetchall())
    return {"books": books, "tags": tags, "recommendations": recommendations}


def normalize_catalog(books: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized_books: list[dict[str, Any]] = []
    source_counter: Counter[str] = Counter()
    canonical_counter: Counter[str] = Counter()
    unmapped_counter: Counter[str] = Counter()
    dropped_counter: Counter[tuple[str, str]] = Counter()
    alias_counter: Counter[tuple[str, str]] = Counter()
    suppressed_counter: Counter[str] = Counter()
    capped_counter: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    diffs: list[dict[str, Any]] = []

    for book in books:
        result = normalize_tags(book.get("tags"))
        normalized = dict(book)
        normalized["tags"] = result.tags
        normalized_books.append(normalized)

        source_counter.update(result.source_labels)
        canonical_counter.update(result.tags)
        unmapped_counter.update(result.unmapped)
        suppressed_counter.update(result.suppressed)
        capped_counter.update(result.capped)
        for label, reason in result.dropped.items():
            dropped_counter[(label, reason)] += 1
        for label, outputs in result.mapped.items():
            for output in outputs:
                if label != output:
                    alias_counter[(label, output)] += 1
        for label in result.unmapped:
            titles = samples.setdefault(label, [])
            if len(titles) < 3 and book["title"] not in titles:
                titles.append(book["title"])

        old_tags = sorted(set(book.get("tags") or []))
        new_tags = result.tags
        if old_tags != sorted(new_tags):
            diffs.append(
                {
                    "book_id": book["id"],
                    "title": book["title"],
                    "before_count": len(old_tags),
                    "after_count": len(new_tags),
                    "before_tags": "; ".join(old_tags),
                    "after_tags": "; ".join(new_tags),
                }
            )

    zero_tag_books = [book for book in normalized_books if not book["tags"]]
    audit = {
        "source_counter": source_counter,
        "canonical_counter": canonical_counter,
        "unmapped_counter": unmapped_counter,
        "dropped_counter": dropped_counter,
        "alias_counter": alias_counter,
        "suppressed_counter": suppressed_counter,
        "capped_counter": capped_counter,
        "unmapped_samples": samples,
        "diffs": diffs,
        "zero_tag_books": zero_tag_books,
    }
    return normalized_books, audit


def validation_errors(books: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    zero_tag_books = [book for book in books if not book.get("tags")]
    if zero_tag_books:
        sample = ", ".join(book["title"] for book in zero_tag_books[:5])
        errors.append(f"{len(zero_tag_books)} books would have zero tags (examples: {sample})")

    over_limit = [book for book in books if len(book.get("tags") or []) > MAX_TAGS_PER_BOOK]
    if over_limit:
        errors.append(f"{len(over_limit)} books exceed the {MAX_TAGS_PER_BOOK}-tag limit")

    unknown = sorted(
        {
            tag
            for book in books
            for tag in book.get("tags") or []
            if tag not in CANONICAL_TAG_SET
        }
    )
    if unknown:
        errors.append(f"unknown canonical outputs: {', '.join(unknown)}")
    return errors


def write_audit_artifacts(
    run_dir: Path,
    books: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    audit: dict[str, Any],
    errors: list[str],
) -> None:
    run_dir.mkdir(parents=True, exist_ok=False)

    with (run_dir / "book_diffs.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "book_id",
            "title",
            "before_count",
            "after_count",
            "before_tags",
            "after_tags",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit["diffs"])

    with (run_dir / "unmapped_tags.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["tag", "occurrence_count", "sample_books"],
        )
        writer.writeheader()
        for tag, count in audit["unmapped_counter"].most_common():
            writer.writerow(
                {
                    "tag": tag,
                    "occurrence_count": count,
                    "sample_books": " | ".join(audit["unmapped_samples"].get(tag, [])),
                }
            )

    tag_counts = [len(book["tags"]) for book in books]
    summary = {
        "mode": "dry-run",
        "book_count": len(books),
        "changed_book_count": len(audit["diffs"]),
        "recommendation_count_after": len(recommendations),
        "assignments_before": sum(audit["source_counter"].values()),
        "assignments_after": sum(audit["canonical_counter"].values()),
        "unique_labels_before": len(audit["source_counter"]),
        "unique_labels_after": len(audit["canonical_counter"]),
        "tags_per_book": {
            "median": percentile(tag_counts, 50),
            "p95": percentile(tag_counts, 95),
            "maximum": max(tag_counts, default=0),
        },
        "zero_tag_book_count": len(audit["zero_tag_books"]),
        "unmapped_assignment_count": sum(audit["unmapped_counter"].values()),
        "dropped_assignment_count": sum(audit["dropped_counter"].values()),
        "dropped_by_reason": dict(
            Counter(
                {
                    reason: sum(
                        count
                        for (_label, item_reason), count in audit["dropped_counter"].items()
                        if item_reason == reason
                    )
                    for reason in {item[1] for item in audit["dropped_counter"]}
                }
            ).most_common()
        ),
        "suppressed_assignment_count": sum(audit["suppressed_counter"].values()),
        "capped_assignment_count": sum(audit["capped_counter"].values()),
        "top_alias_rollups": [
            {"source": source, "canonical": output, "count": count}
            for (source, output), count in audit["alias_counter"].most_common(25)
        ],
        "top_unmapped": [
            {"tag": tag, "count": count}
            for tag, count in audit["unmapped_counter"].most_common(25)
        ],
        "validation_errors": errors,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )


def write_backup(snapshot: dict[str, list[dict[str, Any]]], backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=False)
    tags_path = backup_dir / "book_tags.csv"
    recommendations_path = backup_dir / "book_recommendations.csv"

    with tags_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["book_id", "tag"])
        writer.writeheader()
        writer.writerows(snapshot["tags"])

    with recommendations_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["book_id", "similar_book_id", "score", "reasons"],
        )
        writer.writeheader()
        for row in snapshot["recommendations"]:
            writer.writerow(
                {
                    "book_id": row["book_id"],
                    "similar_book_id": row["similar_book_id"],
                    "score": row["score"],
                    "reasons": json.dumps(row.get("reasons") or []),
                }
            )

    book_ids = [book["id"] for book in snapshot["books"]]
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "book_count": len(book_ids),
        "book_id_hash": catalog_id_hash(book_ids),
        "tag_count": len(snapshot["tags"]),
        "recommendation_count": len(snapshot["recommendations"]),
        "files": {
            tags_path.name: sha256_path(tags_path),
            recommendations_path.name: sha256_path(recommendations_path),
        },
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return backup_dir


def load_backup(backup_dir: Path) -> tuple[dict[str, Any], list[tuple[str, str]], list[dict[str, Any]]]:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Backup manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for filename, expected_hash in manifest.get("files", {}).items():
        path = backup_dir / filename
        if not path.exists() or sha256_path(path) != expected_hash:
            raise RuntimeError(f"Backup file is missing or has a checksum mismatch: {path}")

    with (backup_dir / "book_tags.csv").open(newline="", encoding="utf-8") as handle:
        tags = [(row["book_id"], row["tag"]) for row in csv.DictReader(handle)]

    recommendations: list[dict[str, Any]] = []
    with (backup_dir / "book_recommendations.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        for row in csv.DictReader(handle):
            recommendations.append(
                {
                    "book_id": row["book_id"],
                    "similar_book_id": row["similar_book_id"],
                    "score": float(row["score"]),
                    "reasons": json.loads(row["reasons"]),
                }
            )
    return manifest, tags, recommendations


def replace_tag_and_recommendation_rows(
    database_url: str,
    *,
    expected_book_ids: list[str],
    tag_rows: list[tuple[str, str]],
    recommendations: list[dict[str, Any]],
) -> None:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("select id from public.books order by id")
            current_book_ids = [row[0] for row in cur.fetchall()]
            if current_book_ids != sorted(expected_book_ids):
                raise RuntimeError("Hosted book IDs changed after preview; refusing to write.")

            cur.execute("delete from public.book_recommendations")
            cur.execute("delete from public.book_tags")
            if tag_rows:
                cur.executemany(TAG_INSERT, tag_rows)
            if recommendations:
                cur.executemany(
                    RECOMMENDATION_INSERT,
                    [
                        (
                            row["book_id"],
                            row["similar_book_id"],
                            row["score"],
                            row["reasons"],
                        )
                        for row in recommendations
                    ],
                )

            cur.execute("select count(*) from public.books")
            if cur.fetchone()[0] != len(expected_book_ids):
                raise RuntimeError("Book count changed during maintenance transaction.")
            cur.execute(
                """
                select count(*)
                from public.book_recommendations r
                left join public.books b on b.id = r.book_id
                left join public.books s on s.id = r.similar_book_id
                where b.id is null or s.id is null
                """
            )
            if cur.fetchone()[0] != 0:
                raise RuntimeError("Orphan recommendations detected; rolling back.")
        conn.commit()


def apply_cleanup(
    database_url: str,
    report_root: Path,
    snapshot: dict[str, list[dict[str, Any]]],
    normalized_books: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
) -> Path:
    backup_dir = report_root / "backups" / utc_run_id("pre-cleanup")
    write_backup(snapshot, backup_dir)
    tag_rows = [
        (book["id"], tag)
        for book in normalized_books
        for tag in book.get("tags") or []
    ]
    replace_tag_and_recommendation_rows(
        database_url,
        expected_book_ids=[book["id"] for book in normalized_books],
        tag_rows=tag_rows,
        recommendations=recommendations,
    )
    return backup_dir


def restore_backup(database_url: str, report_root: Path, backup_dir: Path, *, apply: bool) -> None:
    manifest, tag_rows, recommendations = load_backup(backup_dir)
    snapshot = load_snapshot(database_url)
    current_book_ids = [book["id"] for book in snapshot["books"]]
    if catalog_id_hash(current_book_ids) != manifest.get("book_id_hash"):
        raise RuntimeError("Current hosted catalog IDs do not match the backup manifest.")

    print(
        f"Restore preview: {manifest['book_count']} books, "
        f"{len(tag_rows)} tags, {len(recommendations)} recommendations."
    )
    if not apply:
        print("Dry-run only. Re-run with --apply to restore this backup.")
        return

    safety_dir = report_root / "backups" / utc_run_id("pre-restore")
    write_backup(snapshot, safety_dir)
    replace_tag_and_recommendation_rows(
        database_url,
        expected_book_ids=current_book_ids,
        tag_rows=tag_rows,
        recommendations=recommendations,
    )
    print(f"Restore applied. Pre-restore safety backup: {safety_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit or transactionally normalize hosted BookLens tags.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the previewed cleanup or restore. Omit for dry-run.",
    )
    parser.add_argument(
        "--restore",
        type=Path,
        help="Preview or restore a timestamped backup directory.",
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        default=DEFAULT_REPORT_ROOT,
        help="Ignored directory for audit artifacts and backups.",
    )
    args = parser.parse_args()

    database_url = get_database_url()
    if args.restore:
        restore_backup(database_url, args.report_root, args.restore, apply=args.apply)
        return

    snapshot = load_snapshot(database_url)
    normalized_books, audit = normalize_catalog(snapshot["books"])
    errors = validation_errors(normalized_books)
    recommendations = recommendations_for_books(normalized_books)

    run_dir = args.report_root / "runs" / utc_run_id("audit")
    write_audit_artifacts(run_dir, normalized_books, recommendations, audit, errors)
    print(
        f"Audit complete: {len(normalized_books)} books, "
        f"{sum(audit['source_counter'].values())} -> "
        f"{sum(audit['canonical_counter'].values())} tag assignments, "
        f"{len(audit['unmapped_counter'])} unique unmapped labels."
    )
    print(f"Audit artifacts: {run_dir}")

    if errors:
        for error in errors:
            print(f"BLOCKED: {error}")
        if args.apply:
            raise RuntimeError("Cleanup validation failed; hosted data was not changed.")
        return

    if not args.apply:
        print("Dry-run only. Re-run with --apply only after explicit production approval.")
        return

    backup_dir = apply_cleanup(
        database_url,
        args.report_root,
        snapshot,
        normalized_books,
        recommendations,
    )
    print(f"Cleanup applied. Rollback backup: {backup_dir}")


if __name__ == "__main__":
    main()
