from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.collect_loc_books import (
    LocClient,
    LocRateLimitError,
    candidate_from_item,
    collect_loc_books,
    normalize_loc_url,
    parse_explicit_isbns,
)


def loc_detail(item_id: str = "demo") -> dict[str, Any]:
    return {
        "item": {
            "id": f"http://www.loc.gov/item/{item_id}/",
            "title": "A Library Adventure",
            "contributor_names": ["Writer, Ada, 1850-1910"],
            "date_issued": "1899",
            "summary": ["A catalog summary."],
            "subjects": ["Fantasy fiction", "Juvenile fiction", "Unmapped heading"],
            "number_isbn": ["ISBN 978-1-4028-9462-6"],
            "rights_advisory": ["Rights status not evaluated."],
            "access_restricted": False,
        }
    }


class FakeClient:
    def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if url == "https://www.loc.gov/books/":
            return {
                "results": [{"id": "http://www.loc.gov/item/demo/"}],
                "pagination": {"next": None},
            }
        self.assert_item_request(url, params)
        return loc_detail()

    @staticmethod
    def assert_item_request(url: str, params: dict[str, Any] | None) -> None:
        if url != "https://www.loc.gov/item/demo/" or params != {"fo": "json", "at": "item"}:
            raise AssertionError((url, params))


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)
        self.headers = {"content-type": "application/json"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    def get(self, *_args: Any, **_kwargs: Any) -> FakeResponse:
        return self.response


class LocCollectorTests(unittest.TestCase):
    def test_normalizes_only_loc_item_urls(self) -> None:
        self.assertEqual(
            normalize_loc_url("http://loc.gov/item/abc?fo=json"),
            "https://www.loc.gov/item/abc/",
        )
        self.assertIsNone(normalize_loc_url("https://www.loc.gov/resource/abc"))
        self.assertIsNone(normalize_loc_url("https://example.com/item/abc"))

    def test_maps_heterogeneous_item_metadata_without_cover_or_inference(self) -> None:
        candidate, reasons = candidate_from_item(
            "http://www.loc.gov/item/demo/",
            loc_detail(),
            ["fantasy fiction"],
        )
        self.assertEqual(reasons, [])
        assert candidate is not None
        self.assertEqual(candidate["provider_id"], "https://www.loc.gov/item/demo/")
        self.assertEqual(candidate["author"], "Writer, Ada, 1850-1910")
        self.assertEqual(candidate["publication_year"], 1899)
        self.assertEqual(candidate["tags"], ["fantasy", "children's literature"])
        self.assertEqual(candidate["tag_unmapped"], ["unmapped heading"])
        self.assertIsNone(candidate["cover_url"])
        self.assertEqual(candidate["isbns"][0]["isbn"], "9781402894626")
        self.assertIn("rights_advisory", candidate["raw_payload"])

    def test_excludes_missing_required_metadata_and_zero_tags(self) -> None:
        candidate, reasons = candidate_from_item(
            "https://www.loc.gov/item/bad/",
            {"item": {"title": "Untaggable", "date_issued": "1900"}},
            ["biography"],
        )
        self.assertIsNone(candidate)
        self.assertIn("missing contributor", reasons)
        self.assertIn("zero canonical tags", reasons)

    def test_isbn_parser_uses_only_explicit_fields(self) -> None:
        values = parse_explicit_isbns(
            {"number": ["9781402894626"], "number_isbn": ["0-306-40615-2"]},
            {},
        )
        self.assertEqual([item["isbn"] for item in values], ["0306406152"])

    def test_rate_limit_response_aborts_without_retry(self) -> None:
        client = LocClient(
            contact=None,
            sleep_seconds=0,
            session=FakeSession(FakeResponse(429, {"error": "slow down"})),
            sleep_fn=lambda _seconds: None,
        )
        with self.assertRaises(LocRateLimitError):
            client.get_json("https://www.loc.gov/books/")

    def test_collection_writes_isolated_raw_and_processed_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            candidates, report = collect_loc_books(
                client=FakeClient(),  # type: ignore[arg-type]
                subjects=["fantasy fiction"],
                limit_per_subject=1,
                limit_total=1,
                data_dir=data_dir,
                resume=False,
            )
            self.assertEqual(len(candidates), 1)
            self.assertEqual(report["candidate_count"], 1)
            self.assertTrue((data_dir / "raw" / "loc" / "checkpoint.json").exists())
            self.assertTrue((data_dir / "raw" / "loc" / "search.jsonl").exists())
            self.assertTrue((data_dir / "raw" / "loc" / "items.jsonl").exists())
            self.assertTrue((data_dir / "processed" / "loc" / "candidates.json").exists())
            self.assertTrue(
                (data_dir / "processed" / "loc" / "collection_report.txt").exists()
            )


if __name__ == "__main__":
    unittest.main()
