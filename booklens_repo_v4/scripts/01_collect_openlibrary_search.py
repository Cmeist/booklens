"""
Collect a BookLens starter dataset from Open Library's public Search API.

This script uses API endpoints instead of scraping HTML pages. Open Library asks
high-frequency clients to identify themselves with a User-Agent and contact email
and to cache responses where possible.

Example:
    python scripts/01_collect_openlibrary_search.py \
      --contact your_email@example.com \
      --limit-per-subject 150 \
      --out data/raw/openlibrary_books.csv
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests

OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"

DEFAULT_SUBJECTS = [
    "fiction",
    "fantasy",
    "science_fiction",
    "romance",
    "mystery",
    "thriller",
    "historical_fiction",
    "young_adult",
    "horror",
    "biography",
    "classics",
    "literary_fiction",
    "nonfiction",
]

FIELDS = [
    "key",
    "title",
    "author_name",
    "first_publish_year",
    "subject",
    "number_of_pages_median",
    "ratings_average",
    "ratings_count",
    "cover_i",
    "edition_count",
    "language",
    "first_sentence",
]


@dataclass(frozen=True)
class CollectorConfig:
    contact: str
    limit_per_subject: int
    page_size: int
    sleep_seconds: float
    subjects: list[str]
    out: str
    debug_dir: str | None = None


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        value = " ".join(str(v) for v in value if v is not None)
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text or None


def normalize_tag(tag: Any) -> str | None:
    text = normalize_text(tag)
    if not text:
        return None
    text = text.lower()
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"[^a-z0-9 &'/.]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def stable_id(openlibrary_key: str, title: str | None, author: str | None) -> str:
    raw = f"{openlibrary_key}|{title or ''}|{author or ''}".lower().encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def cover_url_from_id(cover_i: Any) -> str | None:
    if cover_i is None or str(cover_i).strip() == "":
        return None
    return f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"


def parse_first_sentence(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return normalize_text(value[0])
    return normalize_text(value)


def parse_book(doc: dict[str, Any], source_subject: str) -> dict[str, Any] | None:
    title = normalize_text(doc.get("title"))
    authors = doc.get("author_name") or []
    author = normalize_text(authors[0]) if authors else None
    key = normalize_text(doc.get("key"))

    if not title or not author or not key:
        return None

    raw_tags = doc.get("subject") or []
    tags: list[str] = []
    seen_tags: set[str] = set()

    source_tag = normalize_tag(source_subject)
    if source_tag:
        tags.append(source_tag)
        seen_tags.add(source_tag)

    for raw_tag in raw_tags:
        tag = normalize_tag(raw_tag)
        if tag and tag not in seen_tags:
            tags.append(tag)
            seen_tags.add(tag)
        if len(tags) >= 20:
            break

    return {
        "book_id": stable_id(key, title, author),
        "openlibrary_work_key": key,
        "title": title,
        "author": author,
        "description": parse_first_sentence(doc.get("first_sentence")),
        "tags": "|".join(tags),
        "primary_source_tag": source_tag,
        "publication_year": doc.get("first_publish_year"),
        "page_count": doc.get("number_of_pages_median"),
        "rating_count": doc.get("ratings_count"),
        "average_rating": doc.get("ratings_average"),
        "cover_url": cover_url_from_id(doc.get("cover_i")),
        "edition_count": doc.get("edition_count"),
        "language": "|".join(doc.get("language") or []),
        "source": "openlibrary_search_api",
    }


def get_with_retries(session: requests.Session, url: str, *, params: dict[str, Any], retries: int = 3) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, params=params, timeout=30)
            if response.status_code == 429:
                wait = 2 * attempt
                print(f"Rate limited. Waiting {wait}s before retry {attempt}/{retries}...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            wait = 2 * attempt
            print(f"Request failed ({exc}). Waiting {wait}s before retry {attempt}/{retries}...")
            time.sleep(wait)
    raise RuntimeError(f"Open Library request failed after {retries} attempts: {last_error}")


def fetch_subject_page(
    session: requests.Session,
    subject: str,
    offset: int,
    limit: int,
    query_mode: str,
) -> list[dict[str, Any]]:
    if query_mode == "subject_key":
        q = f"subject_key:{subject}"
    else:
        q = f"subject:{subject.replace('_', ' ')}"

    params = {
        "q": q,
        "fields": ",".join(FIELDS),
        "limit": limit,
        "offset": offset,
        "sort": "rating",
    }
    response = get_with_retries(session, OPENLIBRARY_SEARCH_URL, params=params)
    payload = response.json()
    return payload.get("docs", [])


def merge_book(existing: dict[str, Any], parsed: dict[str, Any]) -> None:
    existing_tags = set(tag for tag in (existing.get("tags") or "").split("|") if tag)
    new_tags = [tag for tag in (parsed.get("tags") or "").split("|") if tag]
    for tag in new_tags:
        existing_tags.add(tag)
    existing["tags"] = "|".join(sorted(existing_tags))

    for col in ["description", "page_count", "rating_count", "average_rating", "cover_url"]:
        if not existing.get(col) and parsed.get(col):
            existing[col] = parsed[col]


def collect(config: CollectorConfig) -> pd.DataFrame:
    headers = {
        "User-Agent": f"BookLensStudentProject/0.2 ({config.contact})",
        "From": config.contact,
    }
    session = requests.Session()
    session.headers.update(headers)

    books_by_id: OrderedDict[str, dict[str, Any]] = OrderedDict()

    for subject in config.subjects:
        print(f"\nCollecting subject={subject!r}")
        collected_docs_for_subject = 0
        offset = 0
        empty_modes = 0

        while collected_docs_for_subject < config.limit_per_subject:
            current_limit = min(config.page_size, config.limit_per_subject - collected_docs_for_subject)

            docs: list[dict[str, Any]] = []
            for query_mode in ["subject_key", "subject"]:
                docs = fetch_subject_page(session, subject, offset, current_limit, query_mode)
                if docs:
                    break
                empty_modes += 1

            if not docs:
                print(f"No more docs for subject={subject!r} at offset={offset}")
                break

            parsed_count = 0
            for doc in docs:
                parsed = parse_book(doc, subject)
                if not parsed:
                    continue
                parsed_count += 1
                if parsed["book_id"] not in books_by_id:
                    books_by_id[parsed["book_id"]] = parsed
                else:
                    merge_book(books_by_id[parsed["book_id"]], parsed)

            collected_docs_for_subject += len(docs)
            offset += len(docs)
            print(f"  fetched={len(docs):3d}, parsed={parsed_count:3d}, total_unique={len(books_by_id):5d}")
            time.sleep(config.sleep_seconds)

            if len(docs) < current_limit:
                break

    df = pd.DataFrame(books_by_id.values())
    if df.empty:
        return df

    df = df.drop_duplicates(subset=["openlibrary_work_key"], keep="first")
    sort_cols = [col for col in ["rating_count", "average_rating", "title"] if col in df.columns]
    if sort_cols:
        ascending = [False if col != "title" else True for col in sort_cols]
        df = df.sort_values(sort_cols, ascending=ascending, na_position="last")
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contact", required=True, help="Your email. Used in API headers per Open Library guidance.")
    parser.add_argument("--limit-per-subject", type=int, default=150)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--sleep-seconds", type=float, default=0.35)
    parser.add_argument("--subjects", nargs="*", default=DEFAULT_SUBJECTS)
    parser.add_argument("--out", default="data/raw/openlibrary_books.csv")
    args = parser.parse_args()

    if args.limit_per_subject < 1:
        raise ValueError("--limit-per-subject must be at least 1")
    if args.page_size < 1 or args.page_size > 100:
        raise ValueError("--page-size should be between 1 and 100")

    config = CollectorConfig(
        contact=args.contact,
        limit_per_subject=args.limit_per_subject,
        page_size=args.page_size,
        sleep_seconds=args.sleep_seconds,
        subjects=args.subjects,
        out=args.out,
    )

    try:
        df = collect(config)
    except Exception as exc:
        print("\nCollection failed.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        print("\nTry the offline demo first: python run_pipeline.py --mode demo", file=sys.stderr)
        raise

    if df.empty:
        raise RuntimeError("No books were collected. Try fewer/custom subjects or run demo mode first.")

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nWrote {len(df):,} unique books to {output_path}")


if __name__ == "__main__":
    main()
