from __future__ import annotations

import unittest

from scripts.tag_normalization import (
    CANONICAL_TAG_SET,
    GENRE_FORM_TAGS,
    MAX_TAGS_PER_BOOK,
    normalize_tags,
    split_source_tags,
)


class TagNormalizationTests(unittest.TestCase):
    def test_parses_supported_inputs_and_normalizes_syntax(self) -> None:
        self.assertEqual(
            split_source_tags(" Young-Adult | SCIENCE_FICTION; young adult "),
            ["young adult", "science fiction"],
        )
        self.assertEqual(split_source_tags(["Fantasy", " fantasy ", "Magic"]), ["fantasy", "magic"])

    def test_consolidates_aliases_and_composites(self) -> None:
        result = normalize_tags(
            "fiction; fiction, historical, general; historical fiction; "
            "young adult fantasy; fantasy fiction; science fiction & fantasy"
        )
        self.assertEqual(
            result.tags,
            ["fantasy", "science fiction", "historical fiction", "young adult"],
        )
        self.assertEqual(result.dropped["fiction"], "generic")
        self.assertEqual(result.mapped["young adult fantasy"], ["young adult", "fantasy"])

    def test_representative_problem_labels_roll_up(self) -> None:
        cases = {
            "classic literature; classic; fiction / classics": ["classics"],
            "detective and mystery stories; mystery fiction": ["mystery"],
            "suspense; suspense fiction; fiction, thrillers, general": ["thriller"],
            "juvenile fiction; children's fiction; children's stories": [
                "children's literature"
            ],
            "fiction, science fiction, action & adventure": ["science fiction", "adventure"],
            "fiction, mystery & detective, women sleuths": ["mystery", "women detectives"],
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(normalize_tags(source).tags, expected)

    def test_distinguishes_junk_from_unmapped_subjects(self) -> None:
        result = normalize_tags(
            "general; large type books; english language; reading level grade 12; "
            "open library staff picks; social life and customs; young women, fiction"
        )
        self.assertEqual(result.tags, [])
        self.assertEqual(result.dropped["general"], "generic")
        self.assertEqual(result.dropped["large type books"], "edition/format")
        self.assertEqual(result.dropped["english language"], "language/catalog")
        self.assertEqual(result.dropped["reading level grade 12"], "edition/format")
        self.assertEqual(result.dropped["open library staff picks"], "catalog/list")
        self.assertEqual(result.unmapped, ["social life and customs", "young women, fiction"])

    def test_suppresses_redundant_parent_tags(self) -> None:
        result = normalize_tags(
            "romance; love; private investigators; detectives; war fiction; war; "
            "paranormal fiction; supernatural; london; england"
        )
        self.assertEqual(
            result.tags,
            ["romance", "paranormal fiction", "war fiction", "private investigators", "london"],
        )
        self.assertCountEqual(
            result.suppressed,
            ["love", "detectives", "war", "supernatural", "england"],
        )

    def test_enforces_stable_priority_and_cap(self) -> None:
        source = list(reversed(GENRE_FORM_TAGS[: MAX_TAGS_PER_BOOK + 4]))
        result = normalize_tags(source)
        self.assertEqual(result.tags, list(GENRE_FORM_TAGS[:MAX_TAGS_PER_BOOK]))
        self.assertEqual(result.capped, list(GENRE_FORM_TAGS[MAX_TAGS_PER_BOOK : MAX_TAGS_PER_BOOK + 4]))

    def test_every_source_label_is_classified(self) -> None:
        result = normalize_tags("fantasy; fiction; unknown useful topic")
        classified = set(result.mapped) | set(result.dropped) | set(result.unmapped)
        self.assertEqual(classified, set(result.source_labels))
        self.assertTrue(set(result.tags) <= CANONICAL_TAG_SET)

    def test_rejects_invalid_limit(self) -> None:
        with self.assertRaises(ValueError):
            normalize_tags("fantasy", limit=0)


if __name__ == "__main__":
    unittest.main()
