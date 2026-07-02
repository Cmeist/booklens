"""
Sparse metadata smoke test for the BookLens pipeline.

Exercises recommendation generation when descriptions are blank or contain only
stop words, and when rating/page metadata is missing. Does not write web fixtures.

Run from the repo root:

    uv run python scripts/smoke_sparse_metadata.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_pipeline import (  # noqa: E402
    REASON_SIMILAR_DESCRIPTION,
    build_recommendations,
    compute_description_similarity,
    normalize_dataframe,
)


def assert_no_similar_description_reasons(recommendations: pd.DataFrame) -> None:
    for reasons in recommendations["reasons"].astype(str):
        if REASON_SIMILAR_DESCRIPTION in reasons:
            raise AssertionError(
                f"Unexpected {REASON_SIMILAR_DESCRIPTION!r} reason for blank/stop-word descriptions: {reasons!r}"
            )


def run_case(name: str, raw_rows: list[dict[str, object]]) -> None:
    books = normalize_dataframe(pd.DataFrame(raw_rows))
    similarity = compute_description_similarity(books["description"])
    recommendations = build_recommendations(books)

    if similarity.shape != (len(books), len(books)):
        raise AssertionError(f"{name}: unexpected similarity shape {similarity.shape}")

    if similarity.sum() != 0:
        raise AssertionError(f"{name}: expected zero description similarity matrix")

    if recommendations.empty and len(books) > 1:
        raise AssertionError(f"{name}: expected recommendations for multi-book input")

    assert_no_similar_description_reasons(recommendations)
    print(f"PASS {name}: {len(books)} books, {len(recommendations)} recommendations")


def main() -> None:
    blank_descriptions = [
        {
            "title": "Alpha",
            "author": "Author A",
            "description": "",
            "tags": "fantasy; adventure",
            "publication_year": 1990,
            "page_count": "",
            "rating_count": "",
            "average_rating": "",
            "cover_url": "",
            "source": "smoke",
            "source_id": "alpha",
        },
        {
            "title": "Beta",
            "author": "Author B",
            "description": "",
            "tags": "fantasy; classics",
            "publication_year": 1992,
            "page_count": "",
            "rating_count": "",
            "average_rating": "",
            "cover_url": "",
            "source": "smoke",
            "source_id": "beta",
        },
        {
            "title": "Gamma",
            "author": "Author C",
            "description": "",
            "tags": "science fiction",
            "publication_year": 2001,
            "page_count": "",
            "rating_count": "",
            "average_rating": "",
            "cover_url": "",
            "source": "smoke",
            "source_id": "gamma",
        },
    ]

    stop_word_descriptions = [
        {
            "title": "Stop One",
            "author": "Writer One",
            "description": "the and or but",
            "tags": "mystery",
            "publication_year": 1980,
            "page_count": 200,
            "rating_count": "",
            "average_rating": "",
            "cover_url": "",
            "source": "smoke",
            "source_id": "stop-one",
        },
        {
            "title": "Stop Two",
            "author": "Writer Two",
            "description": "a an the",
            "tags": "mystery; thriller",
            "publication_year": 1981,
            "page_count": 210,
            "rating_count": "",
            "average_rating": "",
            "cover_url": "",
            "source": "smoke",
            "source_id": "stop-two",
        },
    ]

    run_case("blank descriptions + missing rating/page fields", blank_descriptions)
    run_case("stop-word-only descriptions + missing ratings", stop_word_descriptions)
    print("All sparse metadata smoke tests passed.")


if __name__ == "__main__":
    main()
