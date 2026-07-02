"""
Optionally enrich a BookLens dataset with Google Books volume metadata.

Use this after Open Library collection if you want better page counts,
descriptions, categories, covers, or rating fields for some books.
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import pandas as pd
import requests

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"


def clean_text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text or None


def normalize_tag(tag: Any) -> str | None:
    text = clean_text(tag)
    if not text:
        return None
    text = text.lower()
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"[^a-z0-9 &'/.]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def merge_tags(existing: Any, categories: list[Any]) -> str | None:
    tags: list[str] = []
    seen: set[str] = set()
    if existing is not None and not (isinstance(existing, float) and pd.isna(existing)):
        for raw in str(existing).split("|"):
            tag = normalize_tag(raw)
            if tag and tag not in seen:
                tags.append(tag)
                seen.add(tag)
    for category in categories:
        # Google categories are often like "Fiction / Mystery & Detective / General".
        for piece in str(category).split("/"):
            tag = normalize_tag(piece)
            if tag and tag not in seen:
                tags.append(tag)
                seen.add(tag)
    return "|".join(tags[:25]) if tags else None


def first_volume(session: requests.Session, title: str, author: str, api_key: str | None) -> dict[str, Any] | None:
    query = f'intitle:"{title}"+inauthor:"{author}"'
    params: dict[str, Any] = {
        "q": query,
        "maxResults": 1,
        "printType": "books",
        "projection": "lite",
    }
    if api_key:
        params["key"] = api_key
    response = session.get(GOOGLE_BOOKS_URL, params=params, timeout=30)
    if response.status_code == 429:
        raise RuntimeError("Google Books rate limit reached. Try again later or pass --api-key.")
    response.raise_for_status()
    items = response.json().get("items") or []
    return items[0] if items else None


def enrich(input_path: str, output_path: str, max_rows: int, sleep_seconds: float, api_key: str | None) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    for col in ["description", "page_count", "average_rating", "rating_count", "cover_url", "tags"]:
        if col not in df.columns:
            df[col] = None

    session = requests.Session()
    session.headers.update({"User-Agent": "BookLensStudentProject/0.2"})

    checked = 0
    updated = 0
    for idx, row in df.iterrows():
        if checked >= max_rows:
            break
        title = clean_text(row.get("title"))
        author = clean_text(row.get("author"))
        if not title or not author:
            continue

        # Prioritize rows missing data.
        needs_any = any(not clean_text(row.get(col)) for col in ["description", "page_count", "cover_url"])
        if not needs_any:
            continue

        try:
            volume = first_volume(session, title, author, api_key)
        except Exception as exc:
            print(f"Google Books lookup failed for {title!r}: {exc}")
            break

        checked += 1
        if not volume:
            continue
        info = volume.get("volumeInfo") or {}
        changed = False

        replacements = {
            "description": info.get("description"),
            "page_count": info.get("pageCount"),
            "average_rating": info.get("averageRating"),
            "rating_count": info.get("ratingsCount"),
        }
        image_links = info.get("imageLinks") or {}
        replacements["cover_url"] = image_links.get("thumbnail") or image_links.get("smallThumbnail")

        for col, value in replacements.items():
            if value and not clean_text(row.get(col)):
                df.at[idx, col] = value
                changed = True

        categories = info.get("categories") or []
        merged_tags = merge_tags(row.get("tags"), categories)
        if merged_tags and merged_tags != row.get("tags"):
            df.at[idx, "tags"] = merged_tags
            changed = True

        if changed:
            updated += 1
        if checked % 25 == 0:
            print(f"Checked {checked} Google Books volumes; updated {updated} rows")
        time.sleep(sleep_seconds)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Wrote Google-enriched dataset to {output_path}. Checked={checked}, updated={updated}")
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/books_openlibrary_enriched.csv")
    parser.add_argument("--out", default="data/processed/books_enriched.csv")
    parser.add_argument("--max-rows", type=int, default=300)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()
    enrich(args.input, args.out, args.max_rows, args.sleep_seconds, args.api_key)


if __name__ == "__main__":
    main()
