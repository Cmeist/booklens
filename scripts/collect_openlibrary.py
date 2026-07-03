import argparse
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

DEFAULT_SUBJECTS = [
    "fantasy",
    "science_fiction",
    "romance",
    "mystery",
    "thriller",
    "historical_fiction",
    "young_adult",
    "classics",
    "biography",
    "literary_fiction",
]


def get_json(
    url: str,
    headers: dict[str, str],
    timeout: int = 45,
    max_attempts: int = 3,
    sleep_seconds: float = 2.0,
) -> dict[str, Any] | None:
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            print(f"Request failed, attempt {attempt}/{max_attempts}: {url}")
            print(f"  {exc}")

            if attempt < max_attempts:
                time.sleep(sleep_seconds * attempt)

    return None


def normalize_description(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("value", ""))
    return ""


def parse_subjects(raw_subjects: str | None) -> list[str]:
    if not raw_subjects:
        return list(DEFAULT_SUBJECTS)

    subjects = [subject.strip() for subject in raw_subjects.split(",") if subject.strip()]
    if not subjects:
        raise ValueError("At least one subject is required when --subjects is provided.")
    return subjects


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


def collect_books(
    contact: str,
    subjects: list[str],
    limit_per_subject: int,
    limit_total: int | None,
    sleep_seconds: float,
) -> pd.DataFrame:
    headers = {
        "User-Agent": f"BookLens student portfolio project ({contact})",
    }

    rows: list[dict[str, Any]] = []
    seen_work_keys: set[str] = set()

    for subject in subjects:
        if limit_total is not None and len(rows) >= limit_total:
            break

        subject_url = (
            f"https://openlibrary.org/subjects/{subject}.json"
            f"?limit={limit_per_subject}"
        )

        print(f"Collecting subject: {subject}")
        subject_data = get_json(subject_url, headers=headers)

        if subject_data is None:
            print(f"Skipping subject after repeated failures: {subject}")
            continue

        for work in subject_data.get("works", []):
            if limit_total is not None and len(rows) >= limit_total:
                break

            work_key = work.get("key")

            if not work_key or work_key in seen_work_keys:
                continue

            seen_work_keys.add(work_key)

            work_url = f"https://openlibrary.org{work_key}.json"
            work_detail = get_json(work_url, headers=headers)

            if work_detail is None:
                print(f"Skipping work after repeated failures: {work_key}")
                continue

            authors = work.get("authors") or []
            author_names = [
                author.get("name", "").strip()
                for author in authors
                if author.get("name")
            ]

            subjects = work_detail.get("subjects") or work.get("subject") or []
            tags = "; ".join(
                sorted(set(str(tag).strip().lower() for tag in subjects if tag))
            )

            cover_id = work.get("cover_id")
            cover_url = (
                f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
                if cover_id
                else ""
            )

            rows.append(
                {
                    "title": work.get("title", "").strip(),
                    "author": "; ".join(author_names),
                    "description": normalize_description(work_detail.get("description")),
                    "tags": tags,
                    "publication_year": work.get("first_publish_year"),
                    "page_count": "",
                    "rating_count": "",
                    "average_rating": "",
                    "cover_url": cover_url,
                    "source": "openlibrary",
                    "source_id": work_key,
                    "seed_subject": subject,
                }
            )

            time.sleep(sleep_seconds)

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect book metadata from Open Library subject pages."
    )
    parser.add_argument(
        "--contact",
        default=None,
        help="Contact email for API User-Agent; defaults to BOOKLENS_CONTACT_EMAIL",
    )
    parser.add_argument(
        "--subjects",
        default=None,
        help="Comma-separated Open Library subjects (default: built-in genre list)",
    )
    parser.add_argument("--limit-per-subject", type=int, default=25)
    parser.add_argument(
        "--limit-total",
        type=int,
        default=None,
        help="Stop after collecting this many unique works across all subjects",
    )
    parser.add_argument("--sleep-seconds", type=float, default=0.25)
    parser.add_argument("--out", default=str(RAW_DIR / "openlibrary_books.csv"))
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    try:
        contact = resolve_contact(args.contact)
        subjects = parse_subjects(args.subjects)
    except ValueError as exc:
        parser.error(str(exc))

    if args.limit_total is not None and args.limit_total < 1:
        parser.error("--limit-total must be at least 1.")

    books = collect_books(
        contact=contact,
        subjects=subjects,
        limit_per_subject=args.limit_per_subject,
        limit_total=args.limit_total,
        sleep_seconds=args.sleep_seconds,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    books.to_csv(out_path, index=False)

    print(f"Wrote {len(books)} rows to {out_path}")


if __name__ == "__main__":
    main()
