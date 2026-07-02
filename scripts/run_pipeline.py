from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
WEB_DATA_DIR = ROOT / "apps" / "web" / "src" / "data"

MAX_RECOMMENDATIONS = 5
CURRENT_YEAR = 2026

REASON_SHARED_TAG = "Shared tag"
REASON_SIMILAR_DESCRIPTION = "Similar description"
REASON_SAME_AUTHOR = "Same author"
REASON_SAME_ERA = "Same publication era"
REASON_SIMILAR_LENGTH = "Similar length"
REASON_SIMILAR_RATING = "Similar rating profile"

COLUMN_ALIASES = {
    "title": "title",
    "author": "author",
    "description": "description",
    "tags": "tags",
    "publication_year": "publication_year",
    "publicationyear": "publication_year",
    "page_count": "page_count",
    "pagecount": "page_count",
    "rating_count": "rating_count",
    "ratingcount": "rating_count",
    "average_rating": "average_rating",
    "averagerating": "average_rating",
    "cover_url": "cover_url",
    "coverurl": "cover_url",
    "source": "source",
    "source_id": "source_id",
    "sourceid": "source_id",
}

DEMO_BOOKS = [
    {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "description": "A fantasy adventure about Bilbo Baggins, a reluctant hobbit who joins a quest involving dwarves, treasure, and a dragon.",
        "tags": "fantasy; adventure; classics",
        "publication_year": 1937,
        "page_count": 310,
        "rating_count": 4200000,
        "average_rating": 4.28,
        "cover_url": "",
        "source": "demo",
        "source_id": "the-hobbit",
    },
    {
        "title": "Dune",
        "author": "Frank Herbert",
        "description": "A science fiction epic about politics, ecology, religion, and power on the desert planet Arrakis.",
        "tags": "science fiction; classics; politics",
        "publication_year": 1965,
        "page_count": 688,
        "rating_count": 1300000,
        "average_rating": 4.27,
        "cover_url": "",
        "source": "demo",
        "source_id": "dune",
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "description": "A classic romance and social comedy about manners, family, class, and misunderstanding.",
        "tags": "classics; romance; literary fiction",
        "publication_year": 1813,
        "page_count": 279,
        "rating_count": 4100000,
        "average_rating": 4.29,
        "cover_url": "",
        "source": "demo",
        "source_id": "pride-and-prejudice",
    },
    {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "description": "A science fiction novel exploring gender, politics, culture, and human connection on a distant planet.",
        "tags": "science fiction; literary fiction; classics",
        "publication_year": 1969,
        "page_count": 304,
        "rating_count": 190000,
        "average_rating": 4.10,
        "cover_url": "",
        "source": "demo",
        "source_id": "the-left-hand-of-darkness",
    },
]


def normalize_column_name(name: str) -> str:
    key = re.sub(r"[^a-z0-9]", "", name.strip().lower())
    return COLUMN_ALIASES.get(key, name.strip().lower())


def clean_text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    text = re.sub(r"\s+", " ", text)
    return text


def parse_tags(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    tags: list[str] = []
    seen: set[str] = set()
    for raw in re.split(r"[;|]", str(value)):
        tag = raw.strip().lower()
        tag = re.sub(r"[_-]+", " ", tag)
        tag = re.sub(r"\s+", " ", tag).strip()
        if tag and tag != "nan" and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def tags_to_string(tags: list[str]) -> str:
    return "; ".join(tags)


def to_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        return round(float(text), 3)
    except ValueError:
        return None


def to_decade(year: int | None) -> str | None:
    if year is None:
        return None
    decade_start = year // 10 * 10
    return f"{decade_start}s"


def normalize_author(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


def stable_id(source: str | None, source_id: str | None, title: str, author: str) -> str:
    if source and source_id:
        raw = f"{source}:{source_id}"
    else:
        raw = f"{title.strip().lower()}:{normalize_author(author)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_raw_dataframe(use_openlibrary: bool, input_path: Path | None) -> pd.DataFrame:
    if input_path is not None:
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        return pd.read_csv(input_path)

    if use_openlibrary:
        openlibrary_path = RAW_DIR / "openlibrary_books.csv"
        if not openlibrary_path.exists():
            raise FileNotFoundError(
                f"Open Library input not found: {openlibrary_path}. "
                "Run scripts/collect_openlibrary.py first or use demo mode."
            )
        return pd.read_csv(openlibrary_path)

    return pd.DataFrame(DEMO_BOOKS)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for column in df.columns:
        renamed[column] = normalize_column_name(str(column))
    df = df.rename(columns=renamed)

    for column in COLUMN_ALIASES.values():
        if column not in df.columns:
            df[column] = None

    cleaned_rows: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        title = clean_text(row.get("title"))
        author = clean_text(row.get("author"))
        if not title or not author:
            continue

        tags = parse_tags(row.get("tags"))
        publication_year = to_int(row.get("publication_year"))
        page_count = to_int(row.get("page_count"))
        rating_count = to_int(row.get("rating_count"))
        average_rating = to_float(row.get("average_rating"))
        cover_url = clean_text(row.get("cover_url"))
        source = clean_text(row.get("source")) or "unknown"
        source_id = clean_text(row.get("source_id")) or ""

        if publication_year is not None and (
            publication_year < 1400 or publication_year > CURRENT_YEAR
        ):
            publication_year = None

        if page_count is not None and (page_count < 1 or page_count > 5000):
            page_count = None

        if average_rating is not None and (average_rating < 0 or average_rating > 5):
            average_rating = None

        if rating_count is not None and rating_count < 0:
            rating_count = None

        book_id = stable_id(source, source_id or None, title, author)

        cleaned_rows.append(
            {
                "id": book_id,
                "title": title,
                "author": author,
                "description": clean_text(row.get("description")) or "",
                "tags": tags_to_string(tags),
                "tag_list": tags,
                "publication_year": publication_year,
                "decade": to_decade(publication_year),
                "page_count": page_count,
                "rating_count": rating_count,
                "average_rating": average_rating,
                "cover_url": cover_url,
                "source": source,
                "source_id": source_id,
            }
        )

    cleaned = pd.DataFrame(cleaned_rows)
    if cleaned.empty:
        return cleaned

    cleaned = cleaned.drop_duplicates(subset=["id"], keep="first")
    return cleaned.sort_values(["title", "author"]).reset_index(drop=True)


def build_top_tags(df: pd.DataFrame) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    for tags in df["tag_list"]:
        counter.update(tags)

    rows = [{"tag": tag, "book_count": count} for tag, count in counter.most_common()]
    return pd.DataFrame(rows)


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def similar_length(left: int | None, right: int | None) -> bool:
    if left is None or right is None or left <= 0 or right <= 0:
        return False
    ratio = abs(left - right) / max(left, right)
    return ratio <= 0.15


def similar_rating_profile(
    left_rating: float | None,
    right_rating: float | None,
    left_count: int | None,
    right_count: int | None,
) -> bool:
    if left_rating is None or right_rating is None:
        return False
    if abs(left_rating - right_rating) > 0.25:
        return False
    if left_count is None or right_count is None or left_count <= 0 or right_count <= 0:
        return True
    left_mag = 10 ** int(round(math.log10(left_count)))
    right_mag = 10 ** int(round(math.log10(right_count)))
    if left_mag == 0 or right_mag == 0:
        return True
    ratio = max(left_mag, right_mag) / min(left_mag, right_mag)
    return ratio <= 10


def build_reasons(
    seed: pd.Series,
    candidate: pd.Series,
    description_similarity: float,
) -> list[str]:
    reasons: list[str] = []

    seed_tags = set(seed["tag_list"])
    candidate_tags = set(candidate["tag_list"])
    if seed_tags & candidate_tags:
        reasons.append(REASON_SHARED_TAG)

    if description_similarity >= 0.12:
        reasons.append(REASON_SIMILAR_DESCRIPTION)

    if normalize_author(seed["author"]) == normalize_author(candidate["author"]):
        reasons.append(REASON_SAME_AUTHOR)

    if seed["decade"] and seed["decade"] == candidate["decade"]:
        reasons.append(REASON_SAME_ERA)

    if similar_length(seed["page_count"], candidate["page_count"]):
        reasons.append(REASON_SIMILAR_LENGTH)

    if similar_rating_profile(
        seed["average_rating"],
        candidate["average_rating"],
        seed["rating_count"],
        candidate["rating_count"],
    ):
        reasons.append(REASON_SIMILAR_RATING)

    return reasons


def combined_score(
    description_similarity: float,
    tag_overlap: float,
    same_author: bool,
    same_decade: bool,
    length_match: bool,
    rating_match: bool,
) -> float:
    score = description_similarity * 0.45
    score += tag_overlap * 0.25
    score += 0.10 if same_author else 0.0
    score += 0.08 if same_decade else 0.0
    score += 0.06 if length_match else 0.0
    score += 0.06 if rating_match else 0.0
    return round(score, 4)


def compute_description_similarity(descriptions: pd.Series) -> np.ndarray:
    """Return pairwise description cosine similarity, falling back to zeros when TF-IDF fails.

    Covers empty descriptions, stop-word-only text, and empty vocabularies.
    Sparse metadata coverage: ``uv run python scripts/smoke_sparse_metadata.py``.
    """
    count = len(descriptions)
    if count <= 1:
        return np.zeros((count, count))

    texts = descriptions.fillna("").astype(str).tolist()
    if not any(text.strip() for text in texts):
        return np.zeros((count, count))

    vectorizer = TfidfVectorizer(stop_words="english", min_df=1, max_features=5000)
    try:
        description_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return np.zeros((count, count))

    if description_matrix.shape[1] == 0:
        return np.zeros((count, count))

    return cosine_similarity(description_matrix)


def build_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) <= 1:
        return pd.DataFrame(columns=["book_id", "similar_book_id", "score", "reasons"])

    books = df.reset_index(drop=True)
    description_similarity = compute_description_similarity(books["description"])

    rows: list[dict[str, Any]] = []
    for seed_pos, (_, seed) in enumerate(books.iterrows()):
        scored_candidates: list[tuple[int, float, list[str]]] = []

        for candidate_pos, (_, candidate) in enumerate(books.iterrows()):
            if seed_pos == candidate_pos:
                continue

            desc_sim = float(description_similarity[seed_pos, candidate_pos])
            tag_overlap = jaccard(set(seed["tag_list"]), set(candidate["tag_list"]))
            same_author = normalize_author(seed["author"]) == normalize_author(candidate["author"])
            same_decade = bool(seed["decade"] and seed["decade"] == candidate["decade"])
            length_match = similar_length(seed["page_count"], candidate["page_count"])
            rating_match = similar_rating_profile(
                seed["average_rating"],
                candidate["average_rating"],
                seed["rating_count"],
                candidate["rating_count"],
            )

            score = combined_score(
                desc_sim,
                tag_overlap,
                same_author,
                same_decade,
                length_match,
                rating_match,
            )
            reasons = build_reasons(seed, candidate, desc_sim)

            scored_candidates.append((candidate_pos, score, reasons))

        scored_candidates.sort(key=lambda item: item[1], reverse=True)
        for candidate_pos, score, reasons in scored_candidates[:MAX_RECOMMENDATIONS]:
            candidate = books.iloc[candidate_pos]
            rows.append(
                {
                    "book_id": seed["id"],
                    "similar_book_id": candidate["id"],
                    "score": score,
                    "reasons": "; ".join(reasons),
                }
            )

    return pd.DataFrame(rows)


def nullable_json(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def export_books_json(df: pd.DataFrame, out_path: Path) -> None:
    books = []
    for row in df.to_dict(orient="records"):
        books.append(
            {
                "id": row["id"],
                "title": row["title"],
                "author": row["author"],
                "description": row["description"],
                "tags": row["tag_list"],
                "publicationYear": nullable_json(row["publication_year"]),
                "decade": nullable_json(row["decade"]),
                "pageCount": nullable_json(row["page_count"]),
                "ratingCount": nullable_json(row["rating_count"]),
                "averageRating": nullable_json(row["average_rating"]),
                "coverUrl": nullable_json(row["cover_url"]),
                "source": row["source"],
                "sourceId": row["source_id"],
            }
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(books, indent=2) + "\n", encoding="utf-8")


def export_top_tags_json(top_tags: pd.DataFrame, out_path: Path) -> None:
    payload = [
        {"tag": row["tag"], "bookCount": int(row["book_count"])}
        for row in top_tags.to_dict(orient="records")
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def export_recommendations_json(recommendations: pd.DataFrame, out_path: Path) -> None:
    payload = []
    for row in recommendations.to_dict(orient="records"):
        reasons = [part.strip() for part in str(row["reasons"]).split(";") if part.strip()]
        payload.append(
            {
                "bookId": row["book_id"],
                "similarBookId": row["similar_book_id"],
                "score": float(row["score"]),
                "reasons": reasons,
            }
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_quality_report(
    df: pd.DataFrame,
    top_tags: pd.DataFrame,
    recommendations: pd.DataFrame,
    out_path: Path,
) -> None:
    lines = [
        "BookLens Data Quality Report",
        "============================",
        f"Rows: {len(df)}",
        "",
        "Missing field counts:",
        f"- description: {int((df['description'] == '').sum())}",
        f"- publication_year: {int(df['publication_year'].isna().sum())}",
        f"- page_count: {int(df['page_count'].isna().sum())}",
        f"- rating_count: {int(df['rating_count'].isna().sum())}",
        f"- average_rating: {int(df['average_rating'].isna().sum())}",
        f"- cover_url: {int(df['cover_url'].isna().sum())}",
        "",
        "Top tags:",
    ]

    if top_tags.empty:
        lines.append("- none")
    else:
        for row in top_tags.head(10).to_dict(orient="records"):
            lines.append(f"- {row['tag']}: {row['book_count']}")

    lines.extend(
        [
            "",
            f"Recommendations: {len(recommendations)}",
        ]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(use_openlibrary: bool, input_path: Path | None) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = load_raw_dataframe(use_openlibrary=use_openlibrary, input_path=input_path)
    if not use_openlibrary and input_path is None:
        demo_raw_path = RAW_DIR / "demo_books.csv"
        raw_df.to_csv(demo_raw_path, index=False)
        print(f"Wrote {demo_raw_path}")

    books = normalize_dataframe(raw_df)
    if books.empty:
        raise RuntimeError("No valid books remained after cleaning.")

    export_columns = [
        "id",
        "title",
        "author",
        "description",
        "tags",
        "publication_year",
        "decade",
        "page_count",
        "rating_count",
        "average_rating",
        "cover_url",
        "source",
        "source_id",
    ]
    books_clean_path = PROCESSED_DIR / "books_clean.csv"
    books[export_columns].to_csv(books_clean_path, index=False)
    print(f"Wrote {books_clean_path}")

    top_tags = build_top_tags(books)
    top_tags_path = PROCESSED_DIR / "top_tags.csv"
    top_tags.to_csv(top_tags_path, index=False)
    print(f"Wrote {top_tags_path}")

    recommendations = build_recommendations(books)
    recommendations_path = PROCESSED_DIR / "recommendations.csv"
    recommendations.to_csv(recommendations_path, index=False)
    print(f"Wrote {recommendations_path}")

    report_path = PROCESSED_DIR / "data_quality_report.txt"
    write_quality_report(books, top_tags, recommendations, report_path)
    print(f"Wrote {report_path}")

    books_json_path = WEB_DATA_DIR / "books.sample.json"
    top_tags_json_path = WEB_DATA_DIR / "top-tags.sample.json"
    recommendations_json_path = WEB_DATA_DIR / "recommendations.sample.json"

    export_books_json(books, books_json_path)
    print(f"Wrote {books_json_path}")

    export_top_tags_json(top_tags, top_tags_json_path)
    print(f"Wrote {top_tags_json_path}")

    export_recommendations_json(recommendations, recommendations_json_path)
    print(f"Wrote {recommendations_json_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BookLens data pipeline.")
    parser.add_argument(
        "--openlibrary",
        action="store_true",
        help="Read data/raw/openlibrary_books.csv instead of built-in demo data.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional path to a raw CSV input file.",
    )
    args = parser.parse_args()
    run_pipeline(use_openlibrary=args.openlibrary, input_path=args.input)


if __name__ == "__main__":
    main()
