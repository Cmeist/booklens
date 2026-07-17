from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.import_loc_books import (
    build_preview,
    catalog_fingerprint,
    load_import_backup,
    merged_book,
    primary_author_tokens,
    write_import_backup,
)
from scripts.seed_supabase import BOOK_SOURCE_UPSERT, provider_url_for


def book(
    book_id: str,
    title: str,
    author: str,
    year: int | None,
    *,
    description: str = "Hosted description",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": book_id,
        "title": title,
        "author": author,
        "description": description,
        "publication_year": year,
        "decade": f"{year // 10 * 10}s" if year else None,
        "page_count": 250,
        "rating_count": 10,
        "average_rating": 4.0,
        "cover_url": "https://example.com/cover.jpg",
        "source": "openlibrary",
        "source_id": f"/works/{book_id}",
        "tags": tags or ["classics"],
    }


def candidate(
    item_id: str,
    title: str,
    author: str,
    year: int,
    *,
    isbns: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    provider_id = f"https://www.loc.gov/item/{item_id}/"
    return {
        "provider": "loc",
        "provider_id": provider_id,
        "provider_url": provider_id,
        "title": title,
        "author": author,
        "description": "LoC description",
        "publication_year": year,
        "tags": tags or ["biography"],
        "isbns": [
            {"isbn": value, "isbn_type": "ISBN_13", "provider": "loc"}
            for value in isbns or []
        ],
        "seed_subjects": ["biography"],
        "tag_unmapped": [],
        "raw_payload": {"id": provider_id, "rights": ["Review rights"]},
    }


def snapshot() -> dict[str, list[dict[str, Any]]]:
    books = [
        book("one", "Exact Life", "Jane Writer", 1900, description=""),
        book("two", "ISBN Life", "Other Person", 1910),
        book("near", "Close Life", "Near Author", 1920),
    ]
    tags = [
        {"book_id": item["id"], "tag": tag}
        for item in books
        for tag in item["tags"]
    ]
    return {
        "books": books,
        "tags": tags,
        "sources": [
            {
                "book_id": "one",
                "provider": "openlibrary",
                "provider_id": "/works/one",
                "provider_url": "https://openlibrary.org/works/one",
                "raw_payload": None,
            }
        ],
        "isbns": [
            {
                "book_id": "two",
                "isbn": "9781402894626",
                "isbn_type": "ISBN_13",
                "provider": "openlibrary",
            }
        ],
        "recommendations": [],
        "popularity": [],
    }


class LocImporterTests(unittest.TestCase):
    def test_author_match_tokens_ignore_order_and_catalog_dates(self) -> None:
        self.assertEqual(
            primary_author_tokens("Writer, Jane, 1840-1910"),
            primary_author_tokens("Jane Writer"),
        )

    def test_reconciliation_uses_exact_isbn_bibliographic_and_ambiguous_paths(self) -> None:
        candidates = [
            candidate("exact", "Exact Life", "Writer, Jane, 1840-1910", 1900),
            candidate("isbn", "Different title", "Different author", 1910, isbns=["9781402894626"]),
            candidate("near", "Close Life", "Near Author", 1922),
            candidate("new", "Brand New Life", "New Author", 1930),
        ]
        preview = build_preview(snapshot(), candidates)
        by_provider = {
            row["provider_id"].split("/")[-2]: row for row in preview["classifications"]
        }
        self.assertEqual(by_provider["exact"]["status"], "matched")
        self.assertEqual(by_provider["exact"]["match_on"], "title_author_year")
        self.assertEqual(by_provider["isbn"]["status"], "matched")
        self.assertEqual(by_provider["isbn"]["match_on"], "isbn")
        self.assertEqual(by_provider["near"]["status"], "ambiguous")
        self.assertEqual(by_provider["new"]["status"], "new")

        exact_action = next(
            action for action in preview["actions"] if action["candidate"]["title"] == "Exact Life"
        )
        self.assertEqual(exact_action["after"]["id"], "one")
        self.assertEqual(exact_action["after"]["source"], "openlibrary")
        self.assertEqual(exact_action["after"]["description"], "LoC description")
        self.assertEqual(exact_action["after"]["cover_url"], "https://example.com/cover.jpg")

    def test_merge_preserves_primary_fields_and_caps_canonical_tags(self) -> None:
        hosted = book("one", "Hosted", "Hosted Author", 1900, tags=["romance", "love"])
        merged = merged_book(hosted, candidate("one", "Provider", "Provider Author", 1900))
        self.assertEqual(merged["title"], "Hosted")
        self.assertEqual(merged["author"], "Hosted Author")
        self.assertEqual(merged["source"], "openlibrary")
        self.assertIn("romance", merged["tags"])
        self.assertNotIn("love", merged["tags"])

    def test_fingerprint_is_stable_by_row_order_and_changes_with_catalog_data(self) -> None:
        first = snapshot()
        second = snapshot()
        second["books"].reverse()
        second["tags"].reverse()
        self.assertEqual(catalog_fingerprint(first), catalog_fingerprint(second))
        second["books"][0]["title"] = "Changed"
        self.assertNotEqual(catalog_fingerprint(first), catalog_fingerprint(second))

    def test_backup_manifest_round_trip_checksums(self) -> None:
        current = snapshot()
        preview = build_preview(
            current,
            [candidate("exact", "Exact Life", "Jane Writer", 1900)],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backup"
            write_import_backup(backup_dir, current, preview)
            manifest, content = load_import_backup(backup_dir)
        self.assertEqual(manifest["provider"], "loc")
        self.assertEqual(manifest["pre_fingerprint"], catalog_fingerprint(current))
        self.assertIn("affected_books.json", content)

    def test_shared_source_upsert_cannot_reassign_provider_record(self) -> None:
        update_clause = BOOK_SOURCE_UPSERT.split("do update set", 1)[1].split("where", 1)[0]
        self.assertNotIn("book_id", update_clause)
        self.assertIn("where book_sources.book_id = excluded.book_id", BOOK_SOURCE_UPSERT)
        self.assertEqual(
            provider_url_for("loc", "http://www.loc.gov/item/demo/"),
            "https://www.loc.gov/item/demo/",
        )


if __name__ == "__main__":
    unittest.main()
