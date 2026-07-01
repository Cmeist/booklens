from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


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
    },
]


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    books = pd.DataFrame(DEMO_BOOKS)

    raw_path = RAW_DIR / "demo_books.csv"
    clean_path = PROCESSED_DIR / "books_clean.csv"
    top_tags_path = PROCESSED_DIR / "top_tags.csv"
    report_path = PROCESSED_DIR / "data_quality_report.txt"

    books.to_csv(raw_path, index=False)
    books.to_csv(clean_path, index=False)

    tag_counts = (
        books["tags"]
        .str.split(";")
        .explode()
        .str.strip()
        .value_counts()
        .reset_index()
    )
    tag_counts.columns = ["tag", "book_count"]
    tag_counts.to_csv(top_tags_path, index=False)

    report = [
        "BookLens Data Quality Report",
        "============================",
        f"Rows: {len(books)}",
        f"Columns: {len(books.columns)}",
        f"Missing descriptions: {books['description'].isna().sum()}",
        f"Missing tags: {books['tags'].isna().sum()}",
        f"Top tag: {tag_counts.iloc[0]['tag']}",
    ]
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"Wrote {raw_path}")
    print(f"Wrote {clean_path}")
    print(f"Wrote {top_tags_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
