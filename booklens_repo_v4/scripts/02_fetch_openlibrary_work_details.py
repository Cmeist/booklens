"""
Fetch descriptions and additional subjects from Open Library Work endpoints.

This enriches rows collected from /search.json using the work key, e.g.
/works/OL27448W -> https://openlibrary.org/works/OL27448W.json
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

BASE_URL = "https://openlibrary.org"


def normalize_text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, dict):
        value = value.get("value")
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


def merge_tags(existing: Any, new_tags: list[str]) -> str | None:
    tags: list[str] = []
    seen: set[str] = set()
    if existing is not None and not (isinstance(existing, float) and pd.isna(existing)):
        for raw in str(existing).split("|"):
            tag = normalize_tag(raw)
            if tag and tag not in seen:
                tags.append(tag)
                seen.add(tag)
    for raw in new_tags:
        tag = normalize_tag(raw)
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
        if len(tags) >= 25:
            break
    return "|".join(tags) if tags else None


def get_json(session: requests.Session, url: str, retries: int = 3) -> dict[str, Any] | None:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=30)
            if response.status_code == 404:
                return None
            if response.status_code == 429:
                time.sleep(2 * attempt)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(2 * attempt)
    print(f"Could not fetch {url}: {last_error}")
    return None


def enrich(input_path: str, output_path: str, contact: str, max_works: int, sleep_seconds: float) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    if "description" not in df.columns:
        df["description"] = None
    if "tags" not in df.columns:
        df["tags"] = None

    session = requests.Session()
    session.headers.update({
        "User-Agent": f"BookLensStudentProject/0.2 ({contact})",
        "From": contact,
    })

    updated = 0
    considered = 0
    for idx, row in df.iterrows():
        if considered >= max_works:
            break
        key = normalize_text(row.get("openlibrary_work_key"))
        if not key or not key.startswith("/works/"):
            continue

        needs_description = not normalize_text(row.get("description"))
        # Still fetch some rows with a description because work endpoints can have better subjects.
        if not needs_description and considered >= max_works:
            continue

        url = f"{BASE_URL}{key}.json"
        payload = get_json(session, url)
        considered += 1
        if not payload:
            continue

        desc = normalize_text(payload.get("description"))
        subjects = payload.get("subjects") or []
        new_tags = [t for t in (normalize_tag(s) for s in subjects) if t]

        changed = False
        if desc and needs_description:
            df.at[idx, "description"] = desc
            changed = True
        merged = merge_tags(row.get("tags"), new_tags)
        if merged and merged != row.get("tags"):
            df.at[idx, "tags"] = merged
            changed = True
        if changed:
            updated += 1
        if considered % 25 == 0:
            print(f"Fetched {considered} work records; updated {updated} rows")
        time.sleep(sleep_seconds)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Wrote enriched dataset to {output_path}. Work records fetched={considered}, rows updated={updated}")
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/openlibrary_books.csv")
    parser.add_argument("--out", default="data/processed/books_openlibrary_enriched.csv")
    parser.add_argument("--contact", required=True)
    parser.add_argument("--max-works", type=int, default=300)
    parser.add_argument("--sleep-seconds", type=float, default=0.35)
    args = parser.parse_args()
    enrich(args.input, args.out, args.contact, args.max_works, args.sleep_seconds)


if __name__ == "__main__":
    main()
