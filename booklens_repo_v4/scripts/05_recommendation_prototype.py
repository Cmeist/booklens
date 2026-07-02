"""
Create a simple content-based recommendation sample for BookLens.

The recommender uses title, author, description, tags, publication year bucket,
page count bucket, average rating bucket, and rating count bucket.
"""
from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def safe_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


def bucket_number(value: Any, buckets: list[tuple[float, str]]) -> str:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "unknown"
        x = float(value)
    except Exception:
        return "unknown"
    for upper, label in buckets:
        if x <= upper:
            return label
    return buckets[-1][1]


def decade(value: Any) -> str:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "unknown decade"
        year = int(float(value))
        return f"{year // 10 * 10}s"
    except Exception:
        return "unknown decade"


def feature_text(row: pd.Series) -> str:
    tags = safe_text(row.get("tags")).replace("|", " ")
    page_bucket = bucket_number(row.get("page_count"), [(200, "short book"), (400, "medium length book"), (800, "long book"), (99999, "very long book")])
    rating_bucket = bucket_number(row.get("average_rating"), [(3.5, "lower rated"), (4.0, "solid rated"), (4.3, "highly rated"), (5.0, "very highly rated")])
    popularity_bucket = bucket_number(row.get("rating_count"), [(100, "low rating count"), (1000, "moderate rating count"), (10000, "popular"), (999999999, "very popular")])
    parts = [
        safe_text(row.get("title")),
        safe_text(row.get("author")),
        safe_text(row.get("description")),
        tags,
        decade(row.get("publication_year")),
        page_bucket,
        rating_bucket,
        popularity_bucket,
    ]
    return " ".join(part for part in parts if part)


def top_tags(value: Any, limit: int = 6) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    return [tag.strip() for tag in str(value).split("|") if tag.strip()][:limit]


def explanation(seed: pd.Series, rec: pd.Series) -> str:
    reasons: list[str] = []
    seed_tags = set(top_tags(seed.get("tags"), 10))
    rec_tags = set(top_tags(rec.get("tags"), 10))
    shared = sorted(seed_tags & rec_tags)
    if shared:
        reasons.append("shared tags: " + ", ".join(shared[:4]))

    seed_decade = decade(seed.get("publication_year"))
    rec_decade = decade(rec.get("publication_year"))
    if seed_decade == rec_decade and seed_decade != "unknown decade":
        reasons.append(f"same publication decade: {seed_decade}")

    try:
        if abs(float(seed.get("page_count")) - float(rec.get("page_count"))) <= 75:
            reasons.append("similar page count")
    except Exception:
        pass

    try:
        if abs(float(seed.get("average_rating")) - float(rec.get("average_rating"))) <= 0.2:
            reasons.append("similar average rating")
    except Exception:
        pass

    if not reasons:
        reasons.append("similar description and metadata profile")
    return "; ".join(reasons[:4])


def find_seed_index(df: pd.DataFrame, seed_title: str | None) -> int:
    if not seed_title:
        return 0
    normalized = seed_title.strip().lower()
    matches = df[df["title"].str.lower().str.contains(re.escape(normalized), na=False)]
    if not matches.empty:
        return int(matches.index[0])
    print(f"Seed title {seed_title!r} not found. Using first row instead.")
    return 0


def make_recommendations(input_path: str, out_path: str, seed_title: str | None, top_k: int) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    if df.empty:
        raise RuntimeError("Input dataset is empty.")
    for col in ["title", "author", "description", "tags"]:
        if col not in df.columns:
            df[col] = ""

    df = df.reset_index(drop=True)
    texts = df.apply(feature_text, axis=1)
    vectorizer = TfidfVectorizer(stop_words="english", min_df=1, max_features=5000, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(texts)

    seed_idx = find_seed_index(df, seed_title)
    sims = cosine_similarity(matrix[seed_idx], matrix).ravel()
    ranked = sims.argsort()[::-1]

    rows: list[dict[str, Any]] = []
    seed = df.iloc[seed_idx]
    for idx in ranked:
        if idx == seed_idx:
            continue
        rec = df.iloc[int(idx)]
        rows.append({
            "seed_title": seed.get("title"),
            "recommended_title": rec.get("title"),
            "recommended_author": rec.get("author"),
            "similarity_score": round(float(sims[idx]), 4),
            "explanation": explanation(seed, rec),
            "tags": rec.get("tags"),
            "publication_year": rec.get("publication_year"),
            "page_count": rec.get("page_count"),
            "average_rating": rec.get("average_rating"),
            "rating_count": rec.get("rating_count"),
        })
        if len(rows) >= top_k:
            break

    recs = pd.DataFrame(rows)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    recs.to_csv(out_path, index=False)
    print(f"Wrote recommendation sample to {out_path}")
    return recs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/books_clean.csv")
    parser.add_argument("--out", default="data/processed/similar_books_sample.csv")
    parser.add_argument("--seed-title", default=None)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()
    make_recommendations(args.input, args.out, args.seed_title, args.top_k)


if __name__ == "__main__":
    main()
