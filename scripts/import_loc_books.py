"""Preview, apply, or restore a Library of Congress metadata import.

Dry-run is the default. ``--apply`` is required for hosted writes. The normal
import path never deletes books; deletion is available only through a validated
restore manifest for untouched books inserted by that exact import.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import unicodedata
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

try:
    from scripts.collect_loc_books import normalize_loc_url
    from scripts.run_pipeline import stable_id
    from scripts.seed_supabase import (
        BOOK_SOURCE_UPSERT,
        finish_ingestion_run,
        get_database_url,
        normalize_isbn,
        recommendations_for_books,
        start_ingestion_run,
    )
    from scripts.tag_normalization import CANONICAL_TAG_SET, normalize_tags
except ModuleNotFoundError:  # Direct execution: python scripts/import_loc_books.py
    from collect_loc_books import normalize_loc_url
    from run_pipeline import stable_id
    from seed_supabase import (
        BOOK_SOURCE_UPSERT,
        finish_ingestion_run,
        get_database_url,
        normalize_isbn,
        recommendations_for_books,
        start_ingestion_run,
    )
    from tag_normalization import CANONICAL_TAG_SET, normalize_tags


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "data" / "processed" / "loc" / "candidates.json"
DEFAULT_REPORT_ROOT = ROOT / "data" / "processed" / "loc"

BOOKS_QUERY = """
select
  id, title, author, description, publication_year, decade, page_count,
  rating_count, average_rating, cover_url, source, source_id, created_at, updated_at
from public.books
order by id
"""
TAGS_QUERY = "select book_id, tag from public.book_tags order by book_id, tag"
SOURCES_QUERY = """
select book_id, provider, provider_id, provider_url, raw_payload, fetched_at, created_at
from public.book_sources
order by provider, provider_id
"""
ISBNS_QUERY = """
select book_id, isbn, isbn_type, provider, created_at
from public.book_isbns
order by isbn
"""
RECOMMENDATIONS_QUERY = """
select book_id, similar_book_id, score::float8 as score, reasons
from public.book_recommendations
order by book_id, similar_book_id
"""
POPULARITY_QUERY = """
select id, book_id, provider, provider_id, list_name, rank, published_at, matched_on
from public.book_popularity_signals
order by id
"""

NEW_BOOK_INSERT = """
insert into public.books (
  id, title, author, description, publication_year, decade, page_count,
  rating_count, average_rating, cover_url, source, source_id, created_at, updated_at
) values (
  %(id)s, %(title)s, %(author)s, %(description)s, %(publication_year)s, %(decade)s,
  %(page_count)s, %(rating_count)s, %(average_rating)s, %(cover_url)s, %(source)s,
  %(source_id)s, %(created_at)s, %(updated_at)s
)
"""
MATCHED_BOOK_UPDATE = """
update public.books
set
  description = %(description)s,
  publication_year = %(publication_year)s,
  decade = %(decade)s,
  cover_url = %(cover_url)s
where id = %(id)s
"""
RESTORE_BOOK_UPDATE = """
update public.books
set
  title = %(title)s,
  author = %(author)s,
  description = %(description)s,
  publication_year = %(publication_year)s,
  decade = %(decade)s,
  page_count = %(page_count)s,
  rating_count = %(rating_count)s,
  average_rating = %(average_rating)s,
  cover_url = %(cover_url)s,
  source = %(source)s,
  source_id = %(source_id)s
where id = %(id)s
"""
TAG_INSERT = """
insert into public.book_tags (book_id, tag)
values (%s, %s)
on conflict (book_id, tag) do nothing
"""
SAFE_ISBN_UPSERT = """
insert into public.book_isbns (book_id, isbn, isbn_type, provider)
values (%s, %s, %s, %s)
on conflict (isbn) do update set
  isbn_type = coalesce(public.book_isbns.isbn_type, excluded.isbn_type),
  provider = coalesce(public.book_isbns.provider, excluded.provider)
where public.book_isbns.book_id = excluded.book_id
"""
RECOMMENDATION_INSERT = """
insert into public.book_recommendations (
  book_id, similar_book_id, score, reasons
) values (%s, %s, %s, %s)
"""

BOOK_LOGICAL_FIELDS = (
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
)
SOURCE_LOGICAL_FIELDS = ("book_id", "provider", "provider_id", "provider_url", "raw_payload")
ISBN_LOGICAL_FIELDS = ("book_id", "isbn", "isbn_type", "provider")


def utc_run_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=json_default) + "\n",
        encoding="utf-8",
    )


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def logical_row(row: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {field: row.get(field) for field in fields}


def catalog_fingerprint(snapshot: dict[str, list[dict[str, Any]]]) -> str:
    payload = {
        "books": [
            logical_row(row, BOOK_LOGICAL_FIELDS)
            for row in sorted(snapshot["books"], key=lambda item: item["id"])
        ],
        "tags": [
            logical_row(row, ("book_id", "tag"))
            for row in sorted(snapshot["tags"], key=lambda item: (item["book_id"], item["tag"]))
        ],
        "sources": [
            logical_row(row, SOURCE_LOGICAL_FIELDS)
            for row in sorted(
                snapshot["sources"], key=lambda item: (item["provider"], item["provider_id"])
            )
        ],
        "isbns": [
            logical_row(row, ISBN_LOGICAL_FIELDS)
            for row in sorted(snapshot["isbns"], key=lambda item: item["isbn"])
        ],
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=json_default,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_snapshot_from_connection(conn: psycopg.Connection[Any]) -> dict[str, list[dict[str, Any]]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(BOOKS_QUERY)
        books = [dict(row) for row in cur.fetchall()]
        cur.execute(TAGS_QUERY)
        tags = [dict(row) for row in cur.fetchall()]
        cur.execute(SOURCES_QUERY)
        sources = [dict(row) for row in cur.fetchall()]
        cur.execute(ISBNS_QUERY)
        isbns = [dict(row) for row in cur.fetchall()]
        cur.execute(RECOMMENDATIONS_QUERY)
        recommendations = [dict(row) for row in cur.fetchall()]
        cur.execute(
            "select to_regclass('public.book_popularity_signals') as table_name"
        )
        if cur.fetchone()["table_name"] is not None:
            cur.execute(POPULARITY_QUERY)
            popularity = [dict(row) for row in cur.fetchall()]
        else:
            popularity = []

    tags_by_book: dict[str, list[str]] = defaultdict(list)
    for row in tags:
        tags_by_book[row["book_id"]].append(row["tag"])
    for book in books:
        book["tags"] = tags_by_book.get(book["id"], [])
    return {
        "books": books,
        "tags": tags,
        "sources": sources,
        "isbns": isbns,
        "recommendations": recommendations,
        "popularity": popularity,
    }


def load_snapshot(database_url: str) -> dict[str, list[dict[str, Any]]]:
    with psycopg.connect(database_url) as conn:
        return load_snapshot_from_connection(conn)


def normalize_match_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def primary_author_tokens(value: Any) -> tuple[str, ...]:
    primary = str(value or "").split(";", 1)[0]
    tokens = normalize_match_text(primary).split()
    filtered = [
        token
        for token in tokens
        if not re.fullmatch(r"(?:1[4-9]|20|21)\d{2}", token)
        and token not in {"author", "editor", "translator"}
    ]
    return tuple(sorted(set(filtered)))


def bibliographic_key(record: dict[str, Any]) -> tuple[str, tuple[str, ...], int | None]:
    year = record.get("publication_year")
    return (
        normalize_match_text(record.get("title")),
        primary_author_tokens(record.get("author")),
        int(year) if year is not None else None,
    )


def load_candidates(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"LoC candidate file not found: {path}. Run make collect-loc first."
        )
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise RuntimeError(f"LoC candidate file must contain a JSON list: {path}")
    return [dict(item) for item in value if isinstance(item, dict)]


def prepare_candidate(candidate: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    prepared = copy.deepcopy(candidate)
    reasons: list[str] = []
    provider_id = normalize_loc_url(prepared.get("provider_id"))
    if prepared.get("provider") != "loc":
        reasons.append("provider must be loc")
    if not provider_id:
        reasons.append("invalid LoC provider_id")
    title = str(prepared.get("title") or "").strip()
    author = str(prepared.get("author") or "").strip()
    try:
        year = int(prepared.get("publication_year"))
    except (TypeError, ValueError):
        year = 0
    if not title:
        reasons.append("missing title")
    if not author:
        reasons.append("missing author")
    if not 1400 <= year <= 2100:
        reasons.append("invalid publication year")

    tag_result = normalize_tags(prepared.get("tags"))
    if not tag_result.tags:
        reasons.append("zero canonical tags")
    unknown = sorted(set(tag_result.tags) - CANONICAL_TAG_SET)
    if unknown:
        reasons.append(f"unknown canonical tags: {', '.join(unknown)}")
    if reasons:
        return None, reasons

    isbns: list[dict[str, str | None]] = []
    seen_isbns: set[str] = set()
    for item in prepared.get("isbns") or []:
        if not isinstance(item, dict):
            continue
        isbn = normalize_isbn(str(item.get("isbn") or ""))
        if len(isbn) not in {10, 13} or isbn in seen_isbns:
            continue
        seen_isbns.add(isbn)
        isbns.append(
            {
                "isbn": isbn,
                "isbn_type": item.get("isbn_type") or item.get("isbnType"),
                "provider": "loc",
            }
        )
    prepared.update(
        {
            "provider": "loc",
            "provider_id": provider_id,
            "provider_url": provider_id,
            "title": title,
            "author": author,
            "description": str(prepared.get("description") or "").strip(),
            "publication_year": year,
            "decade": f"{year // 10 * 10}s",
            "page_count": None,
            "rating_count": None,
            "average_rating": None,
            "cover_url": None,
            "tags": tag_result.tags,
            "isbns": isbns,
            "seed_subjects": list(dict.fromkeys(prepared.get("seed_subjects") or [])),
            "raw_payload": prepared.get("raw_payload") or {},
        }
    )
    return prepared, []


def merged_book(existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(existing)
    if not str(merged.get("description") or "").strip():
        merged["description"] = candidate["description"]
    if merged.get("publication_year") is None:
        merged["publication_year"] = candidate["publication_year"]
    if not str(merged.get("decade") or "").strip() and merged.get("publication_year"):
        merged["decade"] = f"{int(merged['publication_year']) // 10 * 10}s"
    if not str(merged.get("cover_url") or "").strip():
        merged["cover_url"] = candidate.get("cover_url")
    merged["tags"] = normalize_tags(
        [*(existing.get("tags") or []), *(candidate.get("tags") or [])]
    ).tags
    return merged


def new_book(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": stable_id("loc", candidate["provider_id"], candidate["title"], candidate["author"]),
        "title": candidate["title"],
        "author": candidate["author"],
        "description": candidate["description"],
        "publication_year": candidate["publication_year"],
        "decade": candidate["decade"],
        "page_count": None,
        "rating_count": None,
        "average_rating": None,
        "cover_url": None,
        "source": "loc",
        "source_id": candidate["provider_id"],
        "tags": candidate["tags"],
    }


def source_row_for_action(action: dict[str, Any]) -> dict[str, Any]:
    candidate = action["candidate"]
    return {
        "book_id": action["book_id"],
        "provider": "loc",
        "provider_id": candidate["provider_id"],
        "provider_url": candidate["provider_url"],
        "raw_payload": candidate.get("raw_payload") or {},
    }


def final_snapshot_for_actions(
    snapshot: dict[str, list[dict[str, Any]]],
    actions: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    final = copy.deepcopy(snapshot)
    books_by_id = {book["id"]: book for book in final["books"]}
    source_by_key = {
        (source["provider"], source["provider_id"]): source for source in final["sources"]
    }
    isbn_by_value = {row["isbn"]: row for row in final["isbns"]}

    for action in actions:
        books_by_id[action["book_id"]] = copy.deepcopy(action["after"])
        source = source_row_for_action(action)
        source_by_key[("loc", source["provider_id"])] = source
        for isbn_record in action["candidate"].get("isbns") or []:
            isbn_by_value[isbn_record["isbn"]] = {
                "book_id": action["book_id"],
                **isbn_record,
            }

    final["books"] = sorted(books_by_id.values(), key=lambda row: row["id"])
    final["tags"] = [
        {"book_id": book["id"], "tag": tag}
        for book in final["books"]
        for tag in book.get("tags") or []
    ]
    final["sources"] = sorted(
        source_by_key.values(), key=lambda row: (row["provider"], row["provider_id"])
    )
    final["isbns"] = sorted(isbn_by_value.values(), key=lambda row: row["isbn"])
    return final


def build_preview(
    snapshot: dict[str, list[dict[str, Any]]],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    books_by_id = {book["id"]: copy.deepcopy(book) for book in snapshot["books"]}
    source_index = {
        (row["provider"], row["provider_id"]): row["book_id"] for row in snapshot["sources"]
    }
    isbn_index: dict[str, set[str]] = defaultdict(set)
    for row in snapshot["isbns"]:
        isbn_index[row["isbn"]].add(row["book_id"])
    exact_index: dict[tuple[str, tuple[str, ...], int | None], list[str]] = defaultdict(list)
    title_author_index: dict[tuple[str, tuple[str, ...]], list[str]] = defaultdict(list)
    for book in snapshot["books"]:
        title, author, year = bibliographic_key(book)
        exact_index[(title, author, year)].append(book["id"])
        title_author_index[(title, author)].append(book["id"])

    classifications: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    proposed_bibliographic: dict[tuple[str, tuple[str, ...], int | None], str] = {}
    proposed_isbns: dict[str, str] = {}
    seen_provider_ids: set[str] = set()

    for raw_candidate in candidates:
        candidate, invalid_reasons = prepare_candidate(raw_candidate)
        if candidate is None:
            classifications.append(
                {
                    "provider_id": raw_candidate.get("provider_id"),
                    "title": raw_candidate.get("title"),
                    "status": "excluded",
                    "match_on": None,
                    "book_id": None,
                    "reasons": invalid_reasons,
                }
            )
            continue
        provider_id = candidate["provider_id"]
        if provider_id in seen_provider_ids:
            classifications.append(
                {
                    "provider_id": provider_id,
                    "title": candidate["title"],
                    "status": "excluded",
                    "match_on": None,
                    "book_id": None,
                    "reasons": ["duplicate provider_id in candidate file"],
                }
            )
            continue
        seen_provider_ids.add(provider_id)

        key = bibliographic_key(candidate)
        title_author_key = key[:2]
        candidate_isbns = {item["isbn"] for item in candidate["isbns"]}
        isbn_books = set().union(*(isbn_index.get(isbn, set()) for isbn in candidate_isbns))
        proposed_conflicts = {
            proposed_isbns[isbn] for isbn in candidate_isbns if isbn in proposed_isbns
        }
        target_id = source_index.get(("loc", provider_id))
        match_on: str | None = "provider_id" if target_id else None
        ambiguous_reasons: list[str] = []

        if len(isbn_books) > 1:
            ambiguous_reasons.append("candidate ISBNs resolve to multiple hosted books")
        if target_id and isbn_books and isbn_books != {target_id}:
            ambiguous_reasons.append("LoC source and ISBN resolve to different books")
        if not target_id and len(isbn_books) == 1:
            target_id = next(iter(isbn_books))
            match_on = "isbn"

        if not target_id and not ambiguous_reasons:
            exact_matches = exact_index.get(key, [])
            if len(exact_matches) == 1:
                target_id = exact_matches[0]
                match_on = "title_author_year"
            elif len(exact_matches) > 1:
                ambiguous_reasons.append("multiple exact title/author/year matches")

        if not target_id and not ambiguous_reasons:
            near_matches: list[str] = []
            for book_id in title_author_index.get(title_author_key, []):
                hosted_year = books_by_id[book_id].get("publication_year")
                if hosted_year is None or abs(int(hosted_year) - int(key[2])) <= 3:
                    near_matches.append(book_id)
            if near_matches:
                ambiguous_reasons.append("title/author match requires publication-year review")
            if key in proposed_bibliographic:
                ambiguous_reasons.append("duplicates a proposed new bibliographic record")
            if proposed_conflicts:
                ambiguous_reasons.append("ISBN duplicates another proposed candidate")

        if ambiguous_reasons:
            classifications.append(
                {
                    "provider_id": provider_id,
                    "title": candidate["title"],
                    "status": "ambiguous",
                    "match_on": match_on,
                    "book_id": target_id,
                    "reasons": ambiguous_reasons,
                }
            )
            continue

        if target_id:
            existing = books_by_id[target_id]
            after = merged_book(existing, candidate)
            status = "matched"
        else:
            after = new_book(candidate)
            target_id = after["id"]
            if target_id in books_by_id:
                classifications.append(
                    {
                        "provider_id": provider_id,
                        "title": candidate["title"],
                        "status": "ambiguous",
                        "match_on": None,
                        "book_id": target_id,
                        "reasons": ["deterministic book ID already exists"],
                    }
                )
                continue
            existing = None
            status = "new"
            proposed_bibliographic[key] = target_id
            for isbn in candidate_isbns:
                proposed_isbns[isbn] = target_id

        action = {
            "status": status,
            "match_on": match_on,
            "book_id": target_id,
            "candidate": candidate,
            "before": copy.deepcopy(existing),
            "after": after,
        }
        actions.append(action)
        books_by_id[target_id] = after
        classifications.append(
            {
                "provider_id": provider_id,
                "title": candidate["title"],
                "status": status,
                "match_on": match_on,
                "book_id": target_id,
                "reasons": [],
            }
        )

    final_snapshot = final_snapshot_for_actions(snapshot, actions)
    recommendations = recommendations_for_books(final_snapshot["books"])
    actionable_subjects = {
        subject
        for action in actions
        for subject in action["candidate"].get("seed_subjects") or []
    }
    errors: list[str] = []
    if len(actions) < 25:
        errors.append(f"pilot has {len(actions)} actionable candidates; at least 25 are required")
    if len(actionable_subjects) < 3:
        errors.append(
            f"pilot covers {len(actionable_subjects)} actionable subject buckets; at least 3 are required"
        )
    if any(not action["after"].get("tags") for action in actions):
        errors.append("one or more actionable books have zero canonical tags")

    status_counts = Counter(item["status"] for item in classifications)
    return {
        "classifications": classifications,
        "actions": actions,
        "final_snapshot": final_snapshot,
        "recommendations": recommendations,
        "pre_fingerprint": catalog_fingerprint(snapshot),
        "post_fingerprint": catalog_fingerprint(final_snapshot),
        "status_counts": dict(status_counts),
        "actionable_subjects": sorted(actionable_subjects),
        "errors": errors,
    }


def scalar_diff(before: dict[str, Any] | None, after: dict[str, Any]) -> dict[str, Any]:
    if before is None:
        return {"insert": logical_row(after, BOOK_LOGICAL_FIELDS), "tags": after.get("tags", [])}
    changes: dict[str, Any] = {}
    for field in (*BOOK_LOGICAL_FIELDS, "tags"):
        if before.get(field) != after.get(field):
            changes[field] = {"before": before.get(field), "after": after.get(field)}
    return changes


def write_preview_artifacts(
    report_root: Path,
    preview: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    apply_requested: bool,
) -> Path:
    run_dir = report_root / "imports" / utc_run_id("apply-preview" if apply_requested else "dry-run")
    run_dir.mkdir(parents=True, exist_ok=False)

    with (run_dir / "classifications.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["provider_id", "title", "status", "match_on", "book_id", "reasons"],
        )
        writer.writeheader()
        for item in preview["classifications"]:
            writer.writerow({**item, "reasons": " | ".join(item["reasons"])})

    diffs = [
        {
            "provider_id": action["candidate"]["provider_id"],
            "status": action["status"],
            "match_on": action["match_on"],
            "book_id": action["book_id"],
            "title": action["candidate"]["title"],
            "changes": scalar_diff(action["before"], action["after"]),
        }
        for action in preview["actions"]
    ]
    write_json(run_dir / "book_diffs.json", diffs)
    write_json(
        run_dir / "ambiguous.json",
        [item for item in preview["classifications"] if item["status"] == "ambiguous"],
    )

    unmapped = Counter(
        label for candidate in candidates for label in candidate.get("tag_unmapped", [])
    )
    with (run_dir / "unmapped_tags.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["tag", "occurrence_count", "sample_books"])
        writer.writeheader()
        for label, count in unmapped.most_common():
            samples = [
                str(candidate.get("title") or "")
                for candidate in candidates
                if label in candidate.get("tag_unmapped", [])
            ][:3]
            writer.writerow(
                {"tag": label, "occurrence_count": count, "sample_books": " | ".join(samples)}
            )

    summary = {
        "mode": "apply-preview" if apply_requested else "dry-run",
        "candidate_count": len(candidates),
        "classifications": preview["status_counts"],
        "actionable_subjects": preview["actionable_subjects"],
        "hosted_book_count_before": len(preview["final_snapshot"]["books"])
        - preview["status_counts"].get("new", 0),
        "hosted_book_count_after": len(preview["final_snapshot"]["books"]),
        "recommendation_count_after": len(preview["recommendations"]),
        "pre_fingerprint": preview["pre_fingerprint"],
        "post_fingerprint": preview["post_fingerprint"],
        "unmapped_assignment_count": sum(unmapped.values()),
        "validation_errors": preview["errors"],
    }
    write_json(run_dir / "summary.json", summary)
    (run_dir / "catalog_fingerprint.txt").write_text(
        f"before {preview['pre_fingerprint']}\nafter  {preview['post_fingerprint']}\n",
        encoding="utf-8",
    )
    return run_dir


def write_import_backup(
    backup_dir: Path,
    snapshot: dict[str, list[dict[str, Any]]],
    preview: dict[str, Any],
) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=False)
    affected_existing_ids = sorted(
        {action["book_id"] for action in preview["actions"] if action["status"] == "matched"}
    )
    inserted = [
        {"book_id": action["book_id"], "provider_id": action["candidate"]["provider_id"]}
        for action in preview["actions"]
        if action["status"] == "new"
    ]
    affected_set = set(affected_existing_ids)
    files = {
        "affected_books.json": [
            book for book in snapshot["books"] if book["id"] in affected_set
        ],
        "affected_tags.json": [
            row for row in snapshot["tags"] if row["book_id"] in affected_set
        ],
        "affected_sources.json": [
            row for row in snapshot["sources"] if row["book_id"] in affected_set
        ],
        "affected_isbns.json": [
            row for row in snapshot["isbns"] if row["book_id"] in affected_set
        ],
        "recommendations.json": snapshot["recommendations"],
        "pre_book_ids.json": [book["id"] for book in snapshot["books"]],
        "inserted_books.json": inserted,
    }
    checksums: dict[str, str] = {}
    for filename, content in files.items():
        path = backup_dir / filename
        write_json(path, content)
        checksums[filename] = sha256_path(path)
    manifest = {
        "version": 1,
        "provider": "loc",
        "created_at": datetime.now(UTC).isoformat(),
        "pre_fingerprint": preview["pre_fingerprint"],
        "post_import_fingerprint": preview["post_fingerprint"],
        "pre_book_count": len(snapshot["books"]),
        "post_book_count": len(preview["final_snapshot"]["books"]),
        "affected_existing_ids": affected_existing_ids,
        "inserted_ids": [row["book_id"] for row in inserted],
        "files": checksums,
    }
    write_json(backup_dir / "manifest.json", manifest)
    return backup_dir


def load_import_backup(backup_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Import backup manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("provider") != "loc" or manifest.get("version") != 1:
        raise RuntimeError("Backup is not a supported LoC import manifest.")
    content: dict[str, Any] = {}
    for filename, expected_hash in manifest.get("files", {}).items():
        path = backup_dir / filename
        if not path.exists() or sha256_path(path) != expected_hash:
            raise RuntimeError(f"Backup file is missing or has a checksum mismatch: {path}")
        content[filename] = json.loads(path.read_text(encoding="utf-8"))
    return manifest, content


def apply_preview(
    database_url: str,
    snapshot: dict[str, list[dict[str, Any]]],
    preview: dict[str, Any],
    report_root: Path,
) -> Path:
    if preview["errors"]:
        raise RuntimeError("LoC import validation failed; refusing to apply.")
    backup_dir = report_root / "backups" / utc_run_id("pre-import")
    write_import_backup(backup_dir, snapshot, preview)

    run_id = uuid.uuid4()
    started_at = datetime.now(UTC)
    start_ingestion_run(
        database_url,
        run_id=run_id,
        provider="loc",
        mode="provider-import",
        requested_count=len(preview["classifications"]),
        started_at=started_at,
    )
    inserted_count = preview["status_counts"].get("new", 0)
    updated_count = preview["status_counts"].get("matched", 0)
    skipped_count = sum(
        preview["status_counts"].get(status, 0) for status in ("ambiguous", "excluded")
    )
    applied_at = datetime.now(UTC)

    try:
        with psycopg.connect(database_url) as conn:
            current = load_snapshot_from_connection(conn)
            if catalog_fingerprint(current) != preview["pre_fingerprint"]:
                raise RuntimeError("Hosted catalog changed after preview; refusing to write.")

            with conn.cursor() as cur:
                for action in preview["actions"]:
                    if action["status"] == "new":
                        payload = {
                            **logical_row(action["after"], BOOK_LOGICAL_FIELDS),
                            "created_at": applied_at,
                            "updated_at": applied_at,
                        }
                        cur.execute(NEW_BOOK_INSERT, payload)
                    else:
                        cur.execute(MATCHED_BOOK_UPDATE, action["after"])
                        if cur.rowcount != 1:
                            raise RuntimeError(f"Matched book disappeared: {action['book_id']}")

                affected_ids = sorted({action["book_id"] for action in preview["actions"]})
                if affected_ids:
                    cur.execute("delete from public.book_tags where book_id = any(%s)", (affected_ids,))
                    tag_rows = [
                        (action["book_id"], tag)
                        for action in preview["actions"]
                        for tag in action["after"].get("tags") or []
                    ]
                    if tag_rows:
                        cur.executemany(TAG_INSERT, tag_rows)

                for action in preview["actions"]:
                    source = source_row_for_action(action)
                    cur.execute(
                        BOOK_SOURCE_UPSERT,
                        {**source, "raw_payload": Jsonb(source["raw_payload"])},
                    )
                    if cur.rowcount != 1:
                        raise RuntimeError(
                            "LoC provider record is assigned to another book: "
                            f"{source['provider_id']}"
                        )
                    for isbn_record in action["candidate"].get("isbns") or []:
                        cur.execute(
                            SAFE_ISBN_UPSERT,
                            (
                                action["book_id"],
                                isbn_record["isbn"],
                                isbn_record.get("isbn_type"),
                                "loc",
                            ),
                        )
                        if cur.rowcount != 1:
                            raise RuntimeError(
                                f"ISBN is assigned to another book: {isbn_record['isbn']}"
                            )

                cur.execute("delete from public.book_recommendations")
                if preview["recommendations"]:
                    cur.executemany(
                        RECOMMENDATION_INSERT,
                        [
                            (
                                row["book_id"],
                                row["similar_book_id"],
                                row["score"],
                                row["reasons"],
                            )
                            for row in preview["recommendations"]
                        ],
                    )

            after = load_snapshot_from_connection(conn)
            actual_fingerprint = catalog_fingerprint(after)
            if actual_fingerprint != preview["post_fingerprint"]:
                raise RuntimeError("Post-import catalog does not match the preview; rolling back.")
            with conn.cursor() as cur:
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
    except Exception as exc:
        try:
            finish_ingestion_run(
                database_url,
                run_id=run_id,
                status="failed",
                inserted_count=0,
                updated_count=0,
                skipped_count=skipped_count,
                error_count=1,
                notes=str(exc)[:2000],
            )
        except Exception:
            pass
        raise

    finish_ingestion_run(
        database_url,
        run_id=run_id,
        status="succeeded",
        inserted_count=inserted_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        error_count=0,
        notes=f"backup={backup_dir}; recommendations={len(preview['recommendations'])}",
    )
    return backup_dir


def restore_import(
    database_url: str,
    backup_dir: Path,
    *,
    apply: bool,
) -> None:
    manifest, backup = load_import_backup(backup_dir)
    snapshot = load_snapshot(database_url)
    current_fingerprint = catalog_fingerprint(snapshot)
    errors: list[str] = []
    if current_fingerprint != manifest["post_import_fingerprint"]:
        errors.append("hosted catalog no longer matches the exact post-import state")
    inserted_ids = set(manifest["inserted_ids"])
    current_ids = {book["id"] for book in snapshot["books"]}
    missing = inserted_ids - current_ids
    if missing:
        errors.append(f"{len(missing)} inserted books are already missing")
    non_loc_sources = [
        row
        for row in snapshot["sources"]
        if row["book_id"] in inserted_ids and row["provider"] != "loc"
    ]
    non_loc_isbns = [
        row
        for row in snapshot["isbns"]
        if row["book_id"] in inserted_ids and row.get("provider") not in {None, "loc"}
    ]
    popularity = [row for row in snapshot["popularity"] if row["book_id"] in inserted_ids]
    if non_loc_sources:
        errors.append("an inserted book gained a non-LoC source")
    if non_loc_isbns:
        errors.append("an inserted book gained a non-LoC ISBN")
    if popularity:
        errors.append("an inserted book gained popularity rows")

    print(
        f"Restore preview: remove {len(inserted_ids)} inserted books, restore "
        f"{len(manifest['affected_existing_ids'])} matched books and "
        f"{len(backup['recommendations.json'])} recommendations."
    )
    for error in errors:
        print(f"BLOCKED: {error}")
    if errors:
        if apply:
            raise RuntimeError("Restore validation failed; hosted data was not changed.")
        return
    if not apply:
        print("Dry-run only. Re-run with --apply only after explicit restore approval.")
        return

    affected_ids = manifest["affected_existing_ids"]
    with psycopg.connect(database_url) as conn:
        current = load_snapshot_from_connection(conn)
        if catalog_fingerprint(current) != manifest["post_import_fingerprint"]:
            raise RuntimeError("Hosted catalog changed after restore preview; refusing to write.")
        with conn.cursor() as cur:
            if inserted_ids:
                cur.execute("delete from public.books where id = any(%s)", (sorted(inserted_ids),))
                if cur.rowcount != len(inserted_ids):
                    raise RuntimeError("Restore did not delete the exact inserted book set.")

            for book in backup["affected_books.json"]:
                cur.execute(RESTORE_BOOK_UPDATE, book)
                if cur.rowcount != 1:
                    raise RuntimeError(f"Affected book disappeared: {book['id']}")
            if affected_ids:
                cur.execute("delete from public.book_tags where book_id = any(%s)", (affected_ids,))
                cur.execute("delete from public.book_sources where book_id = any(%s)", (affected_ids,))
                cur.execute("delete from public.book_isbns where book_id = any(%s)", (affected_ids,))

            tag_rows = [
                (row["book_id"], row["tag"]) for row in backup["affected_tags.json"]
            ]
            if tag_rows:
                cur.executemany(TAG_INSERT, tag_rows)
            for source in backup["affected_sources.json"]:
                cur.execute(
                    BOOK_SOURCE_UPSERT,
                    {
                        **source,
                        "raw_payload": Jsonb(source["raw_payload"])
                        if source.get("raw_payload") is not None
                        else None,
                    },
                )
                if cur.rowcount != 1:
                    raise RuntimeError("Could not restore provider provenance row.")
            for isbn in backup["affected_isbns.json"]:
                cur.execute(
                    SAFE_ISBN_UPSERT,
                    (isbn["book_id"], isbn["isbn"], isbn.get("isbn_type"), isbn.get("provider")),
                )
                if cur.rowcount != 1:
                    raise RuntimeError("Could not restore ISBN row.")

            cur.execute("delete from public.book_recommendations")
            recommendations = backup["recommendations.json"]
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

        restored = load_snapshot_from_connection(conn)
        if catalog_fingerprint(restored) != manifest["pre_fingerprint"]:
            raise RuntimeError("Restored catalog does not match the backup; rolling back.")
        conn.commit()
    print("LoC import restoration applied successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview, apply, or restore Library of Congress candidates."
    )
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", type=Path)
    args = parser.parse_args()

    database_url = get_database_url()
    if args.restore:
        restore_import(database_url, args.restore, apply=args.apply)
        return

    candidates = load_candidates(args.candidates)
    snapshot = load_snapshot(database_url)
    preview = build_preview(snapshot, candidates)
    run_dir = write_preview_artifacts(
        args.report_root,
        preview,
        candidates,
        apply_requested=args.apply,
    )
    print(
        f"LoC import preview: {len(candidates)} candidates; "
        f"{preview['status_counts']}; {len(preview['recommendations'])} recommendations."
    )
    print(f"Audit artifacts: {run_dir}")
    for error in preview["errors"]:
        print(f"BLOCKED: {error}")
    if not args.apply:
        print("Dry-run only. Re-run with --apply only after explicit hosted approval.")
        return
    if preview["errors"]:
        raise RuntimeError("LoC import validation failed; hosted data was not changed.")
    backup_dir = apply_preview(database_url, snapshot, preview, args.report_root)
    print(f"LoC import applied. Restore backup: {backup_dir}")


if __name__ == "__main__":
    main()
