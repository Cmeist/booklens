"""
Clean and validate the BookLens dataset.

Outputs:
- data/processed/books_clean.csv
- data/processed/top_tags.csv
- data/processed/data_quality_report.txt
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

CURRENT_YEAR = 2026

ESSENTIAL_COLUMNS = [
    "book_id",
    "title",
    "author",
    "description",
    "tags",
    "publication_year",
    "page_count",
    "rating_count",
    "average_rating",
    "cover_url",
    "openlibrary_work_key",
    "source",
]


def clean_text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text or None


def clean_tags(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    tags: list[str] = []
    seen: set[str] = set()
    for raw in str(value).split("|"):
        tag = raw.strip().lower()
        tag = re.sub(r"[_-]+", " ", tag)
        tag = re.sub(r"[^a-z0-9 &'/.]+", "", tag)
        tag = re.sub(r"\s+", " ", tag).strip()
        if tag and tag != "nan" and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return "|".join(tags[:25]) if tags else None


def to_int(value: Any) -> int | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return int(float(value))
    except Exception:
        return None


def to_float(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return round(float(value), 3)
    except Exception:
        return None


def tag_counter(series: pd.Series) -> Counter:
    counter: Counter[str] = Counter()
    for value in series.dropna():
        for tag in str(value).split("|"):
            tag = tag.strip()
            if tag:
                counter[tag] += 1
    return counter


def data_quality_report(df: pd.DataFrame, counts: Counter, duplicate_rows_removed: int) -> str:
    lines = [
        "BookLens Data Quality Report",
        "============================",
        f"Rows: {len(df):,}",
        f"Duplicate rows removed: {duplicate_rows_removed:,}",
        "",
        "Missingness:",
    ]
    for col in ESSENTIAL_COLUMNS:
        missing = int(df[col].isna().sum()) if col in df.columns else len(df)
        pct = missing / len(df) * 100 if len(df) else 0
        lines.append(f"- {col}: {missing:,} missing ({pct:.1f}%)")

    lines.extend(["", "Top 10 tags:"])
    if counts:
        for tag, count in counts.most_common(10):
            lines.append(f"- {tag}: {count:,}")
    else:
        lines.append("- No tags found")

    lines.extend(["", "Rating summary:"])
    for col in ["average_rating", "rating_count", "page_count", "publication_year"]:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce").dropna()
            if not numeric.empty:
                lines.append(
                    f"- {col}: min={numeric.min():.1f}, median={numeric.median():.1f}, max={numeric.max():.1f}"
                )
            else:
                lines.append(f"- {col}: no numeric values")
    return "\n".join(lines)


def clean_dataset(input_path: str, output_path: str, top_tags_out: str, report_out: str) -> pd.DataFrame:
    df = pd.read_csv(input_path)

    for col in ESSENTIAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    for col in ["title", "author", "description", "cover_url", "openlibrary_work_key", "source"]:
        df[col] = df[col].apply(clean_text)

    df["tags"] = df["tags"].apply(clean_tags)
    df["publication_year"] = df["publication_year"].apply(to_int)
    df["page_count"] = df["page_count"].apply(to_int)
    df["rating_count"] = df["rating_count"].apply(to_int)
    df["average_rating"] = df["average_rating"].apply(to_float)

    before = len(df)
    df = df.dropna(subset=["title", "author"])
    df = df.drop_duplicates(subset=["title", "author", "publication_year"], keep="first")
    duplicate_rows_removed = before - len(df)

    df = df[(df["publication_year"].isna()) | ((df["publication_year"] >= 1400) & (df["publication_year"] <= CURRENT_YEAR))]
    df = df[(df["page_count"].isna()) | ((df["page_count"] >= 10) & (df["page_count"] <= 3000))]
    df = df[(df["average_rating"].isna()) | ((df["average_rating"] >= 0) & (df["average_rating"] <= 5))]
    df = df[(df["rating_count"].isna()) | (df["rating_count"] >= 0)]

    df = df[ESSENTIAL_COLUMNS]
    df = df.sort_values(["rating_count", "average_rating", "title"], ascending=[False, False, True], na_position="last")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    counts = tag_counter(df["tags"])
    top_tags = pd.DataFrame(counts.most_common(25), columns=["tag", "book_count"])
    Path(top_tags_out).parent.mkdir(parents=True, exist_ok=True)
    top_tags.to_csv(top_tags_out, index=False)

    Path(report_out).parent.mkdir(parents=True, exist_ok=True)
    Path(report_out).write_text(data_quality_report(df, counts, duplicate_rows_removed), encoding="utf-8")

    print(f"Wrote clean dataset to {output_path}")
    print(f"Wrote top tags to {top_tags_out}")
    print(f"Wrote quality report to {report_out}")
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/books_enriched.csv")
    parser.add_argument("--out", default="data/processed/books_clean.csv")
    parser.add_argument("--top-tags-out", default="data/processed/top_tags.csv")
    parser.add_argument("--report-out", default="data/processed/data_quality_report.txt")
    args = parser.parse_args()

    clean_dataset(args.input, args.out, args.top_tags_out, args.report_out)


if __name__ == "__main__":
    main()
