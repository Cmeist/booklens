from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.cleanup_hosted_tags import (
    load_backup,
    normalize_catalog,
    validation_errors,
    write_backup,
)


class HostedTagCleanupTests(unittest.TestCase):
    def test_catalog_audit_and_validation_are_read_only_transformations(self) -> None:
        books = [
            {
                "id": "book-1",
                "title": "Book One",
                "author": "Author",
                "description": "",
                "decade": None,
                "page_count": None,
                "rating_count": None,
                "average_rating": None,
                "tags": ["fiction", "fantasy fiction", "unmapped subject"],
            }
        ]
        normalized, audit = normalize_catalog(books)
        self.assertEqual(normalized[0]["tags"], ["fantasy"])
        self.assertEqual(books[0]["tags"], ["fiction", "fantasy fiction", "unmapped subject"])
        self.assertEqual(audit["unmapped_counter"]["unmapped subject"], 1)
        self.assertEqual(validation_errors(normalized), [])

    def test_zero_tag_books_block_application(self) -> None:
        books = [{"id": "book-1", "title": "Book One", "tags": []}]
        errors = validation_errors(books)
        self.assertTrue(any("zero tags" in error for error in errors))

    def test_backup_round_trip_checksums_and_rows(self) -> None:
        snapshot = {
            "books": [{"id": "book-1"}],
            "tags": [{"book_id": "book-1", "tag": "fantasy"}],
            "recommendations": [
                {
                    "book_id": "book-1",
                    "similar_book_id": "book-2",
                    "score": 0.5,
                    "reasons": ["Shared tag"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backup"
            write_backup(snapshot, backup_dir)
            manifest, tags, recommendations = load_backup(backup_dir)
        self.assertEqual(manifest["book_count"], 1)
        self.assertEqual(tags, [("book-1", "fantasy")])
        self.assertEqual(recommendations[0]["reasons"], ["Shared tag"])


if __name__ == "__main__":
    unittest.main()
