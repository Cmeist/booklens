from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.enrich_google_books import EnrichmentStats, enrich_row
from scripts.run_pipeline import normalize_dataframe, write_unmapped_tags
from scripts.seed_supabase import parse_tags, recommendations_for_books


class TagPipelineTests(unittest.TestCase):
    def test_pipeline_keeps_tag_audit_and_canonical_output(self) -> None:
        source = pd.DataFrame(
            [
                {
                    "title": "Example",
                    "author": "Reader",
                    "description": "",
                    "tags": "fiction; fantasy fiction; unknown useful topic",
                    "source": "fixture",
                    "source_id": "example",
                }
            ]
        )
        books = normalize_dataframe(source)
        row = books.iloc[0]
        self.assertEqual(row["tag_list"], ["fantasy"])
        self.assertEqual(row["tags"], "fantasy")
        self.assertEqual(row["tag_dropped"], {"fiction": "generic"})
        self.assertEqual(row["tag_unmapped"], ["unknown useful topic"])

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "unmapped.csv"
            write_unmapped_tags(books, path)
            report = path.read_text(encoding="utf-8")
        self.assertIn("unknown useful topic,1,Example", report)

    def test_seed_parser_is_a_final_normalization_guard(self) -> None:
        self.assertEqual(
            parse_tags(["fiction, historical, general", "historical fiction", "general"]),
            ["historical fiction"],
        )

    def test_google_categories_are_renormalized_and_unmapped_are_reported(self) -> None:
        stats = EnrichmentStats()
        row = {
            "title": "Example",
            "tags": "fantasy",
            "isbns": "[]",
            "extra_sources": "[]",
        }
        volume = {
            "id": "google-id",
            "volumeInfo": {
                "categories": ["Fiction / Science Fiction / General", "Robots"],
            },
        }
        enriched = enrich_row(row, volume, stats)
        self.assertEqual(enriched["tags"], "fantasy; science fiction")
        self.assertEqual(stats.unmapped_tags["robots"], 1)
        self.assertEqual(stats.unmapped_tag_samples["robots"], ["Example"])

    def test_recommendations_use_normalized_seed_records(self) -> None:
        books = [
            {
                "id": "one",
                "title": "One",
                "author": "A",
                "description": "A magical quest",
                "tags": ["fantasy fiction", "general"],
                "decade": "2000s",
                "page_count": 300,
                "rating_count": 10,
                "average_rating": 4.0,
            },
            {
                "id": "two",
                "title": "Two",
                "author": "B",
                "description": "Another magical quest",
                "tags": ["fiction, fantasy, general"],
                "decade": "2000s",
                "page_count": 310,
                "rating_count": 20,
                "average_rating": 4.1,
            },
        ]
        recommendations = recommendations_for_books(books)
        self.assertEqual(len(recommendations), 2)
        self.assertTrue(all("Shared tag" in item["reasons"] for item in recommendations))
        self.assertEqual(recommendations_for_books([]), [])


if __name__ == "__main__":
    unittest.main()
