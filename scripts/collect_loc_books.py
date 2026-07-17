"""Collect a small, auditable Library of Congress book candidate set.

The collector is intentionally separate from ``run_pipeline.py`` so a LoC
pilot never rewrites the shared processed files or committed web fixtures.
Only bibliographic metadata is fetched; digital files and page resources are
out of scope.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlsplit, urlunsplit

import requests
from dotenv import load_dotenv

try:
    from scripts.seed_supabase import normalize_isbn
    from scripts.tag_normalization import normalize_tags
except ModuleNotFoundError:  # Direct execution: python scripts/collect_loc_books.py
    from seed_supabase import normalize_isbn
    from tag_normalization import normalize_tags


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data"
DEFAULT_SUBJECTS = (
    "fantasy fiction",
    "science fiction",
    "detective and mystery stories",
    "juvenile fiction",
    "biography",
)
SEARCH_URL = "https://www.loc.gov/books/"
MIN_CLI_SLEEP_SECONDS = 3.0


class LocRateLimitError(RuntimeError):
    """Raised when LoC asks the collector to stop rather than retry."""


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def json_default(value: Any) -> str:
    if isinstance(value, (datetime,)):
        return value.isoformat()
    return str(value)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=json_default) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, default=json_default) + "\n")


def parse_subjects(raw_subjects: str | None) -> list[str]:
    if raw_subjects is None:
        return list(DEFAULT_SUBJECTS)
    subjects = [part.strip() for part in raw_subjects.split(",") if part.strip()]
    if not subjects:
        raise ValueError("At least one subject is required.")
    return list(dict.fromkeys(subjects))


def resolve_contact(cli_contact: str | None) -> str | None:
    if cli_contact and cli_contact.strip():
        return cli_contact.strip()
    load_dotenv(ROOT / ".env")
    return os.getenv("BOOKLENS_CONTACT_EMAIL", "").strip() or None


def normalize_loc_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("//"):
        text = f"https:{text}"
    parsed = urlsplit(text)
    host = parsed.netloc.lower()
    if host not in {"loc.gov", "www.loc.gov"} or not parsed.path.startswith("/item/"):
        return None
    path = re.sub(r"/+", "/", parsed.path)
    if not path.endswith("/"):
        path += "/"
    return urlunsplit(("https", "www.loc.gov", path, "", ""))


def scalar_strings(value: Any, *, dictionary_keys: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        values: Iterable[Any] = value.keys() if dictionary_keys else value.values()
        output: list[str] = []
        for item in values:
            output.extend(scalar_strings(item, dictionary_keys=dictionary_keys))
        return output
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        output = []
        for item in value:
            if isinstance(item, dict) and dictionary_keys:
                output.extend(scalar_strings(item, dictionary_keys=True))
            else:
                output.extend(scalar_strings(item, dictionary_keys=dictionary_keys))
        return output
    text = str(value).strip()
    return [text] if text else []


def first_text(*values: Any) -> str:
    for value in values:
        strings = scalar_strings(value)
        if strings:
            return strings[0]
    return ""


def unique_strings(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = re.sub(r"\s+", " ", value).strip(" ;")
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            output.append(cleaned)
    return output


def metadata_labels(value: Any) -> list[str]:
    """Return labels from LoC scalar/list/dictionary facet shapes."""
    return scalar_strings(value, dictionary_keys=True)


def extract_contributors(detail: dict[str, Any], item: dict[str, Any]) -> list[str]:
    named: list[str] = []
    for container in (detail, item):
        named.extend(scalar_strings(container.get("contributor_names")))
    contributors = unique_strings(named)
    if not contributors:
        for container in (detail, item):
            contributors.extend(
                scalar_strings(container.get("contributors"), dictionary_keys=True)
            )
            contributors.extend(
                scalar_strings(container.get("contributor"), dictionary_keys=True)
            )
        contributors = unique_strings(contributors)

    author_entries = [value for value in contributors if re.search(r"\bauthor\b", value, re.I)]
    if author_entries:
        contributors = author_entries
    else:
        non_author_roles = re.compile(
            r"\b(publisher|illustrator|editor|translator|engraver|printer)\b",
            re.I,
        )
        filtered = [value for value in contributors if not non_author_roles.search(value)]
        if filtered:
            contributors = filtered
    return unique_strings(
        re.sub(
            r",?\s*(?:author|publisher|illustrator|editor|translator|engraver|printer)\.?$",
            "",
            value,
            flags=re.I,
        ).rstrip(" .")
        for value in contributors
    )


def parse_publication_year(detail: dict[str, Any], item: dict[str, Any]) -> int | None:
    values = (
        item.get("date_issued"),
        detail.get("date_issued"),
        detail.get("date"),
        item.get("date"),
        item.get("created_published_date"),
        detail.get("created_published"),
        item.get("created_published"),
    )
    for value in values:
        for text in scalar_strings(value):
            for match in re.finditer(r"(?<!\d)(1[4-9]\d{2}|20\d{2}|2100)(?!\d)", text):
                year = int(match.group(1))
                if 1400 <= year <= 2100:
                    return year
    return None


def parse_explicit_isbns(detail: dict[str, Any], item: dict[str, Any]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for field in ("number_isbn", "isbn", "isbns"):
        for container in (detail, item):
            for raw in scalar_strings(container.get(field)):
                for token in re.findall(r"(?:97[89][\d\s-]{10,20}|[\dXx][\dXx\s-]{8,20})", raw):
                    isbn = normalize_isbn(token)
                    if len(isbn) not in {10, 13} or isbn in seen:
                        continue
                    seen.add(isbn)
                    output.append(
                        {
                            "isbn": isbn,
                            "isbn_type": "ISBN_13" if len(isbn) == 13 else "ISBN_10",
                            "provider": "loc",
                        }
                    )
    return output


def compact_raw_payload(
    provider_id: str,
    detail: dict[str, Any],
    item: dict[str, Any],
) -> dict[str, Any]:
    fields = (
        "title",
        "contributor",
        "contributors",
        "contributor_names",
        "summary",
        "description",
        "date",
        "date_issued",
        "created_published",
        "subject",
        "subjects",
        "subject_headings",
        "genre",
        "number_isbn",
        "isbn",
        "isbns",
        "rights",
        "rights_advisory",
        "access_advisory",
        "access_restricted",
        "digitized",
        "language",
    )
    payload: dict[str, Any] = {"id": provider_id}
    for field in fields:
        if field in detail:
            payload[field] = detail[field]
        elif field in item:
            payload[field] = item[field]
    return payload


def candidate_from_item(
    provider_id: str,
    detail: dict[str, Any],
    seed_subjects: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    item_value = detail.get("item")
    item = item_value if isinstance(item_value, dict) else {}
    canonical_url = normalize_loc_url(provider_id) or normalize_loc_url(detail.get("id"))
    title = first_text(detail.get("title"), item.get("title"))

    contributors = extract_contributors(detail, item)
    year = parse_publication_year(detail, item)

    source_labels: list[str] = []
    for field in ("subject", "subjects", "subject_headings", "genre"):
        source_labels.extend(metadata_labels(detail.get(field)))
        source_labels.extend(metadata_labels(item.get(field)))
    source_labels = unique_strings(source_labels)
    tag_result = normalize_tags(source_labels)

    reasons: list[str] = []
    if not canonical_url:
        reasons.append("missing or invalid LoC item URL")
    if not title:
        reasons.append("missing title")
    if not contributors:
        reasons.append("missing contributor")
    if year is None:
        reasons.append("missing publication year between 1400 and 2100")
    if not tag_result.tags:
        reasons.append("zero canonical tags")
    if reasons:
        return None, reasons

    description = first_text(
        detail.get("summary"),
        item.get("summary"),
        detail.get("description"),
        item.get("description"),
    )
    assert canonical_url is not None
    candidate = {
        "provider": "loc",
        "provider_id": canonical_url,
        "provider_url": canonical_url,
        "title": title,
        "author": "; ".join(contributors),
        "description": description,
        "publication_year": year,
        "decade": f"{year // 10 * 10}s",
        "page_count": None,
        "rating_count": None,
        "average_rating": None,
        "cover_url": None,
        "tags": tag_result.tags,
        "source_labels": tag_result.source_labels,
        "tag_mapped": tag_result.mapped,
        "tag_dropped": tag_result.dropped,
        "tag_unmapped": tag_result.unmapped,
        "tag_suppressed": tag_result.suppressed,
        "tag_capped": tag_result.capped,
        "isbns": parse_explicit_isbns(detail, item),
        "seed_subjects": list(dict.fromkeys(seed_subjects)),
        "raw_payload": compact_raw_payload(canonical_url, detail, item),
    }
    return candidate, []


class LocClient:
    def __init__(
        self,
        *,
        contact: str | None,
        sleep_seconds: float = 4.0,
        session: requests.Session | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.sleep_seconds = sleep_seconds
        self.session = session or requests.Session()
        self.sleep_fn = sleep_fn
        self.clock = clock
        self.last_request_at: float | None = None
        user_agent = "BookLens/0.1 Library-of-Congress metadata pilot"
        if contact:
            user_agent += f" ({contact})"
        self.headers = {"User-Agent": user_agent, "Accept": "application/json"}

    def _pace(self) -> None:
        if self.last_request_at is None:
            return
        remaining = self.sleep_seconds - (self.clock() - self.last_request_at)
        if remaining > 0:
            self.sleep_fn(remaining)

    def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            self._pace()
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=45,
                )
                self.last_request_at = self.clock()
                content_type = response.headers.get("content-type", "").lower()
                body_prefix = response.text[:1000].lower()
                if response.status_code == 429 or "captcha" in body_prefix:
                    raise LocRateLimitError(
                        "LoC returned a rate-limit or CAPTCHA response; stop for at least one hour."
                    )
                if response.status_code >= 500:
                    raise requests.HTTPError(
                        f"LoC server error {response.status_code}", response=response
                    )
                response.raise_for_status()
                if "json" not in content_type and body_prefix.lstrip().startswith("<"):
                    raise RuntimeError("LoC returned HTML instead of JSON; collection aborted.")
                payload = response.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("LoC returned a non-object JSON response.")
                return payload
            except LocRateLimitError:
                raise
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                last_error = exc
                if attempt == 3:
                    break
                self.sleep_fn(float(attempt * 2))
        raise RuntimeError(f"LoC request failed after three attempts: {url}: {last_error}")


def load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "records": {}, "search_exclusions": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("records"), dict):
        raise RuntimeError(f"Invalid LoC checkpoint: {path}")
    return value


def save_checkpoint(path: Path, checkpoint: dict[str, Any]) -> None:
    checkpoint["updated_at"] = utc_timestamp()
    write_json(path, checkpoint)


def collect_loc_books(
    *,
    client: LocClient,
    subjects: list[str],
    limit_per_subject: int,
    limit_total: int,
    data_dir: Path,
    resume: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_dir = data_dir / "raw" / "loc"
    processed_dir = data_dir / "processed" / "loc"
    search_path = raw_dir / "search.jsonl"
    items_path = raw_dir / "items.jsonl"
    checkpoint_path = raw_dir / "checkpoint.json"

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    if resume:
        checkpoint = load_checkpoint(checkpoint_path)
    else:
        checkpoint = {
            "version": 1,
            "created_at": utc_timestamp(),
            "records": {},
            "search_exclusions": [],
        }
        search_path.write_text("", encoding="utf-8")
        items_path.write_text("", encoding="utf-8")
        save_checkpoint(checkpoint_path, checkpoint)

    records: dict[str, dict[str, Any]] = checkpoint["records"]
    search_exclusions: list[dict[str, Any]] = checkpoint.setdefault("search_exclusions", [])
    subject_stats: dict[str, dict[str, int]] = {}
    failures: list[dict[str, Any]] = []

    def eligible_candidates() -> list[dict[str, Any]]:
        return [record["candidate"] for record in records.values() if record.get("candidate")]

    for subject in subjects:
        if len(eligible_candidates()) >= limit_total:
            break
        page = 1
        subject_eligible: set[str] = {
            provider_id
            for provider_id, record in records.items()
            if record.get("candidate") and subject in record.get("subjects", [])
        }
        stats = {"search_results": 0, "eligible": len(subject_eligible), "excluded": 0}
        subject_stats[subject] = stats

        while len(subject_eligible) < limit_per_subject:
            if len(eligible_candidates()) >= limit_total:
                break
            search_payload = client.get_json(
                SEARCH_URL,
                params={
                    "fo": "json",
                    "at": "results,pagination",
                    "fa": f"language:english|digitized:true|subject:{subject}",
                    "c": 25,
                    "sp": page,
                },
            )
            append_jsonl(
                search_path,
                {
                    "subject": subject,
                    "page": page,
                    "fetched_at": utc_timestamp(),
                    "response": search_payload,
                },
            )
            results = search_payload.get("results")
            if not isinstance(results, list) or not results:
                break
            stats["search_results"] += len(results)

            for result in results:
                if len(subject_eligible) >= limit_per_subject:
                    break
                if len(eligible_candidates()) >= limit_total:
                    break
                if not isinstance(result, dict):
                    continue
                provider_id = normalize_loc_url(result.get("id"))
                if not provider_id:
                    stats["excluded"] += 1
                    failure = {
                        "subject": subject,
                        "provider_id": None,
                        "raw_id": result.get("id"),
                        "reasons": ["invalid result id"],
                    }
                    failures.append(failure)
                    search_exclusions.append(failure)
                    save_checkpoint(checkpoint_path, checkpoint)
                    continue

                existing = records.get(provider_id)
                if existing:
                    existing_subjects = existing.setdefault("subjects", [])
                    if subject not in existing_subjects:
                        existing_subjects.append(subject)
                    if existing.get("candidate"):
                        candidate_subjects = existing["candidate"].setdefault("seed_subjects", [])
                        if subject not in candidate_subjects:
                            candidate_subjects.append(subject)
                        subject_eligible.add(provider_id)
                        stats["eligible"] = len(subject_eligible)
                    save_checkpoint(checkpoint_path, checkpoint)
                    continue

                try:
                    detail = client.get_json(provider_id, params={"fo": "json", "at": "item"})
                    candidate, reasons = candidate_from_item(provider_id, detail, [subject])
                except LocRateLimitError:
                    save_checkpoint(checkpoint_path, checkpoint)
                    raise
                except Exception as exc:
                    candidate = None
                    reasons = [str(exc)]
                    detail = {"id": provider_id, "collection_error": str(exc)}

                append_jsonl(
                    items_path,
                    {
                        "provider_id": provider_id,
                        "seed_subjects": [subject],
                        "fetched_at": utc_timestamp(),
                        "response": detail,
                    },
                )
                records[provider_id] = {
                    "subjects": [subject],
                    "candidate": candidate,
                    "exclusion_reasons": reasons,
                }
                save_checkpoint(checkpoint_path, checkpoint)
                if candidate:
                    subject_eligible.add(provider_id)
                    stats["eligible"] = len(subject_eligible)
                else:
                    stats["excluded"] += 1
                    failures.append(
                        {"subject": subject, "provider_id": provider_id, "reasons": reasons}
                    )

            pagination = search_payload.get("pagination")
            if not isinstance(pagination, dict) or not pagination.get("next"):
                break
            page += 1

    candidates = eligible_candidates()[:limit_total]
    candidates.sort(key=lambda item: item["provider_id"])
    write_json(processed_dir / "candidates.json", candidates)

    unmapped = Counter(
        label for candidate in candidates for label in candidate.get("tag_unmapped", [])
    )
    dropped = Counter(
        reason
        for candidate in candidates
        for reason in candidate.get("tag_dropped", {}).values()
    )
    report = {
        "generated_at": utc_timestamp(),
        "requested_subjects": subjects,
        "limit_per_subject": limit_per_subject,
        "limit_total": limit_total,
        "candidate_count": len(candidates),
        "completed_item_count": len(records),
        "excluded_count": sum(1 for record in records.values() if not record.get("candidate"))
        + len(search_exclusions),
        "subjects_with_candidates": sum(1 for value in subject_stats.values() if value["eligible"]),
        "subject_stats": subject_stats,
        "top_unmapped_tags": unmapped.most_common(50),
        "dropped_by_reason": dropped.most_common(),
        "failures": [
            *search_exclusions,
            *[
                {
                    "provider_id": provider_id,
                    "subjects": record.get("subjects", []),
                    "reasons": record.get("exclusion_reasons", []),
                }
                for provider_id, record in records.items()
                if not record.get("candidate")
            ],
        ],
    }
    write_json(processed_dir / "collection_report.json", report)
    lines = [
        "Library of Congress collection report",
        f"Generated: {report['generated_at']}",
        f"Candidates: {len(candidates)} / {limit_total}",
        f"Completed item requests: {len(records)}",
        f"Excluded records: {report['excluded_count']}",
        f"Subjects with candidates: {report['subjects_with_candidates']}",
        "",
        "Per-subject results:",
    ]
    for subject, stats in subject_stats.items():
        lines.append(
            f"- {subject}: {stats['eligible']} eligible, "
            f"{stats['excluded']} excluded, {stats['search_results']} search results inspected"
        )
    if unmapped:
        lines.extend(["", "Top unmapped labels:"])
        lines.extend(f"- {label}: {count}" for label, count in unmapped.most_common(25))
    (processed_dir / "collection_report.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return candidates, report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect digitized book metadata from the Library of Congress."
    )
    parser.add_argument("--subjects", help="Comma-separated exact LoC subject facets")
    parser.add_argument("--limit-per-subject", type=int, default=20)
    parser.add_argument("--limit-total", type=int, default=100)
    parser.add_argument("--contact", help="Contact for the User-Agent; defaults to env")
    parser.add_argument("--sleep-seconds", type=float, default=4.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Data root containing raw/loc and processed/loc (default: data)",
    )
    args = parser.parse_args()

    if args.limit_per_subject < 1:
        parser.error("--limit-per-subject must be at least 1")
    if args.limit_total < 1:
        parser.error("--limit-total must be at least 1")
    if args.sleep_seconds < MIN_CLI_SLEEP_SECONDS:
        parser.error(
            f"--sleep-seconds must be at least {MIN_CLI_SLEEP_SECONDS:g} to protect LoC"
        )
    try:
        subjects = parse_subjects(args.subjects)
    except ValueError as exc:
        parser.error(str(exc))

    client = LocClient(
        contact=resolve_contact(args.contact),
        sleep_seconds=args.sleep_seconds,
    )
    candidates, report = collect_loc_books(
        client=client,
        subjects=subjects,
        limit_per_subject=args.limit_per_subject,
        limit_total=args.limit_total,
        data_dir=args.out_dir,
        resume=args.resume,
    )
    print(
        f"Wrote {len(candidates)} candidates across "
        f"{report['subjects_with_candidates']} subjects to "
        f"{args.out_dir / 'processed' / 'loc'}"
    )


if __name__ == "__main__":
    main()
