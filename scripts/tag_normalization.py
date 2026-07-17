"""Canonical BookLens tag normalization.

Provider subjects are intentionally treated as untrusted catalog metadata.  Only
exact aliases in this module can become product tags; everything else is either
classified as known junk or reported as unmapped for later review.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable


MAX_TAGS_PER_BOOK = 16

# Order is product priority, not alphabetical.  It is also the stable output
# order used when a book has more than MAX_TAGS_PER_BOOK mapped concepts.
GENRE_FORM_TAGS = (
    "fantasy",
    "science fiction",
    "mystery",
    "romance",
    "historical fiction",
    "thriller",
    "literary fiction",
    "horror",
    "adventure",
    "crime",
    "psychological fiction",
    "political fiction",
    "paranormal fiction",
    "religious fiction",
    "war fiction",
    "western",
    "espionage",
    "true crime",
    "biography",
    "memoir",
    "classics",
    "drama",
    "poetry",
    "short stories",
    "graphic novels",
    "fairy tales",
    "folklore",
    "mythology",
    "humor",
    "satire",
)

AUDIENCE_TAGS = (
    "children's literature",
    "young adult",
)

THEME_SUBJECT_TAGS = (
    "family",
    "friendship",
    "coming of age",
    "love",
    "magic",
    "good and evil",
    "murder",
    "investigation",
    "private investigators",
    "detectives",
    "women detectives",
    "revenge",
    "survival",
    "war",
    "school",
    "social class",
    "orphans",
    "kidnapping",
    "missing persons",
    "assassins",
    "supernatural",
    "monsters",
    "witches",
    "wizards",
    "vampires",
    "time travel",
    "extraterrestrial life",
    "space exploration",
    "animals",
)

SETTING_PERIOD_TAGS = (
    "england",
    "france",
    "london",
    "new york city",
    "world war ii",
    "victorian era",
    "imaginary places",
)

CANONICAL_TAGS = (
    *GENRE_FORM_TAGS,
    *AUDIENCE_TAGS,
    *THEME_SUBJECT_TAGS,
    *SETTING_PERIOD_TAGS,
)
CANONICAL_TAG_SET = frozenset(CANONICAL_TAGS)
if len(CANONICAL_TAG_SET) != len(CANONICAL_TAGS):
    raise RuntimeError("Canonical tag vocabulary contains duplicate labels.")
TAG_PRIORITY = {tag: position for position, tag in enumerate(CANONICAL_TAGS)}


def normalize_source_label(value: Any) -> str:
    """Normalize syntax only; this function never decides tag meaning."""
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .;:")


def split_source_tags(value: Any) -> list[str]:
    if value is None:
        return []
    try:
        if value != value:  # pandas/numpy NaN without importing either package
            return []
    except (TypeError, ValueError):
        pass

    if isinstance(value, str):
        raw_values: Iterable[Any] = re.split(r"[;|]", value)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, dict)):
        raw_values = value
    else:
        raw_values = [value]

    labels: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        if raw is None:
            continue
        try:
            if raw != raw:
                continue
        except (TypeError, ValueError):
            pass
        label = normalize_source_label(raw)
        if not label or label == "nan" or label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return labels


_RAW_ALIASES: dict[str, tuple[str, ...]] = {
    # Genres and forms.
    "fantasy fiction": ("fantasy",),
    "fiction, fantasy": ("fantasy",),
    "fiction, fantasy, general": ("fantasy",),
    "fiction / fantasy / general": ("fantasy",),
    "english fantasy fiction": ("fantasy",),
    "american fantasy fiction": ("fantasy",),
    "fantastic fiction": ("fantasy",),
    "novela fantástica": ("fantasy",),
    "fantasy & magic": ("fantasy", "magic"),
    "fiction, fantasy, epic": ("fantasy",),
    "young adult fantasy": ("young adult", "fantasy"),
    "science fiction & fantasy": ("science fiction", "fantasy"),
    "fiction, science fiction, general": ("science fiction",),
    "fiction / science fiction / general": ("science fiction",),
    "american science fiction": ("science fiction",),
    "english science fiction": ("science fiction",),
    "fiction, science fiction, action & adventure": ("science fiction", "adventure"),
    "detective and mystery stories": ("mystery",),
    "mystery fiction": ("mystery",),
    "mystery and detective stories": ("mystery",),
    "english detective and mystery stories": ("mystery",),
    "fiction, mystery & detective, general": ("mystery",),
    "fiction / mystery & detective / general": ("mystery",),
    "fiction, mystery & detective, traditional": ("mystery",),
    "fiction, historical, general": ("historical fiction",),
    "fiction, historical": ("historical fiction",),
    "fiction / historical / general": ("historical fiction",),
    "historical": ("historical fiction",),
    "literature and fiction, historical fiction": ("historical fiction",),
    "fiction, thrillers, general": ("thriller",),
    "fiction / thrillers / general": ("thriller",),
    "fiction, thrillers": ("thriller",),
    "fiction, thrillers, suspense": ("thriller",),
    "fiction, thrillers, espionage": ("thriller", "espionage"),
    "fiction, suspense": ("thriller",),
    "suspense": ("thriller",),
    "suspense fiction": ("thriller",),
    "thrillers": ("thriller",),
    "fiction espionage / thriller": ("espionage", "thriller"),
    "fiction, romance, general": ("romance",),
    "fiction / romance / general": ("romance",),
    "romance fiction": ("romance",),
    "love stories": ("romance",),
    "fiction, romance, contemporary": ("romance",),
    "fiction, action & adventure": ("adventure",),
    "action & adventure": ("adventure",),
    "action & adventure fiction": ("adventure",),
    "adventure stories": ("adventure",),
    "adventure fiction": ("adventure",),
    "adventure and adventurers, fiction": ("adventure",),
    "adventure and adventurers": ("adventure",),
    "fiction, crime": ("crime",),
    "crime, fiction": ("crime",),
    "fiction, psychological": ("psychological fiction",),
    "psychological fiction": ("psychological fiction",),
    "fiction, political": ("political fiction",),
    "fiction, war & military": ("war fiction",),
    "war stories": ("war fiction",),
    "fiction, espionage": ("espionage",),
    "spy stories": ("espionage",),
    "spies": ("espionage",),
    "secret service": ("espionage",),
    "intelligence service": ("espionage",),
    "paranormal": ("paranormal fiction",),
    "fiction, paranormal": ("paranormal fiction",),
    "fiction, horror": ("horror",),
    "horror fiction": ("horror",),
    "horror tales": ("horror",),
    "horror stories": ("horror",),
    "fiction, humorous": ("humor",),
    "fiction, humorous, general": ("humor",),
    "humorous stories": ("humor",),
    "comedy": ("humor",),
    "comic books, strips": ("graphic novels",),
    "comic books, strips, etc.": ("graphic novels",),
    "cartoons and comics": ("graphic novels",),
    "fiction, short stories (single author)": ("short stories",),
    "plays": ("drama",),
    "classic": ("classics",),
    "classic literature": ("classics",),
    "fiction, classics": ("classics",),
    "fiction / classics": ("classics",),
    "literary": ("literary fiction",),
    # Audiences.
    "children's fiction": ("children's literature",),
    "children's stories": ("children's literature",),
    "children's literature": ("children's literature",),
    "child and youth fiction": ("children's literature",),
    "juvenile": ("children's literature",),
    "juvenile fiction": ("children's literature",),
    "juvenile literature": ("children's literature",),
    "juvenile works": ("children's literature",),
    "ficción juvenil": ("children's literature",),
    "novela juvenil": ("children's literature",),
    "romans, nouvelles, etc. pour la jeunesse": ("children's literature",),
    "young adult fiction": ("young adult",),
    "ya": ("young adult",),
    # Themes and subjects.
    "families": ("family",),
    "family life": ("family",),
    "fiction, family life": ("family",),
    "fiction, family life, general": ("family",),
    "domestic fiction": ("family",),
    "friendship, fiction": ("friendship",),
    "magic, fiction": ("magic",),
    "private investigators, fiction": ("private investigators",),
    "private investigators in fiction": ("private investigators",),
    "women sleuths": ("women detectives",),
    "fiction, mystery & detective, women sleuths": ("mystery", "women detectives"),
    "fiction, mystery & detective, police procedural": ("mystery", "investigation"),
    "detectives, fiction": ("detectives",),
    "supernatural fiction": ("supernatural",),
    "witches, fiction": ("witches",),
    "schools": ("school",),
    "schools, fiction": ("school",),
    "social classes": ("social class",),
    "extraterrestrial beings": ("extraterrestrial life",),
    "life on other planets": ("extraterrestrial life",),
    "animals, fiction": ("animals",),
    # Settings and periods.
    "england, fiction": ("england",),
    "england fiction": ("england",),
    "london (england), fiction": ("london",),
    "london(england)": ("london",),
    "new york (n.y.), fiction": ("new york city",),
    "france, fiction": ("france",),
    "imaginary places, fiction": ("imaginary places",),
    "world war, 1939 1945": ("world war ii",),
    "world war, 1939 1945, fiction": ("world war ii",),
}


def _normalized_aliases() -> dict[str, tuple[str, ...]]:
    aliases = {tag: (tag,) for tag in CANONICAL_TAGS}
    for raw, outputs in _RAW_ALIASES.items():
        key = normalize_source_label(raw)
        unknown = set(outputs) - CANONICAL_TAG_SET
        if unknown:
            raise RuntimeError(f"Alias {raw!r} emits unknown canonical tags: {sorted(unknown)}")
        aliases[key] = outputs
    return aliases


TAG_ALIASES = _normalized_aliases()

DROP_EXACT: dict[str, str] = {
    # Generic classifications.
    "fiction": "generic",
    "fiction,": "generic",
    "fiction, general": "generic",
    "general": "generic",
    "literature": "generic",
    "history": "generic",
    "novel": "generic",
    "novels": "generic",
    "book": "generic",
    "books": "generic",
    "roman": "generic",
    "romans": "generic",
    "romans, nouvelles": "language/catalog",
    "novela": "language/catalog",
    "ficción": "language/catalog",
    "histoire": "language/catalog",
    "historia": "language/catalog",
    "chang pian xiao shuo": "language/catalog",
    "zhang pian xiao shuo": "language/catalog",
    "english fiction": "generic",
    "american fiction": "generic",
    "fiction in english": "language/catalog",
    "english literature": "generic",
    "american literature": "generic",
    "british": "generic",
    "contemporary": "generic",
    "adult": "generic",
    "children": "generic",
    "stories": "generic",
    # Edition, format, and teaching metadata.
    "large type books": "edition/format",
    "large print books": "edition/format",
    "paperback": "edition/format",
    "readers": "edition/format",
    "readers for new literates": "edition/format",
    "reading materials": "edition/format",
    "dictionaries": "edition/format",
    "specimens": "edition/format",
    "facsimiles": "edition/format",
    "manuscripts": "edition/format",
    # Catalog and list metadata.
    "open library staff picks": "catalog/list",
    "open syllabus project": "catalog/list",
    "long now manual for civilization": "catalog/list",
    "new york times bestseller": "catalog/list",
    "new york times reviewed": "catalog/list",
    "[from old catalog]": "catalog/list",
}

DROP_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^reading level grade \d+$"), "edition/format"),
    (re.compile(r"\b(textbooks?|study and teaching|reading, remedial teaching)\b"), "edition/format"),
    (re.compile(r"\b(language (books?|edition|materials?)|language, textbooks?)\b"), "language/catalog"),
    (re.compile(r"^[a-z]+ language$"), "language/catalog"),
    (re.compile(r"^translations? (into|from)\b"), "language/catalog"),
    (re.compile(r"\b(fictional works by one author|dramatic works by one author)\b"), "catalog/list"),
    (re.compile(r"^\d{3}(?:[./]\S+)?$"), "catalog/list"),
)


REDUNDANCY_RULES: tuple[tuple[str, frozenset[str]], ...] = (
    ("love", frozenset({"romance"})),
    ("detectives", frozenset({"private investigators", "women detectives"})),
    ("war", frozenset({"war fiction"})),
    ("supernatural", frozenset({"paranormal fiction"})),
    ("england", frozenset({"london"})),
)


@dataclass
class TagNormalizationResult:
    source_labels: list[str]
    tags: list[str]
    mapped: dict[str, list[str]] = field(default_factory=dict)
    dropped: dict[str, str] = field(default_factory=dict)
    unmapped: list[str] = field(default_factory=list)
    suppressed: list[str] = field(default_factory=list)
    capped: list[str] = field(default_factory=list)


def _drop_reason(label: str) -> str | None:
    exact = DROP_EXACT.get(label)
    if exact:
        return exact
    for pattern, reason in DROP_PATTERNS:
        if pattern.search(label):
            return reason
    return None


def normalize_tags(value: Any, *, limit: int = MAX_TAGS_PER_BOOK) -> TagNormalizationResult:
    if limit < 1:
        raise ValueError("Tag limit must be at least 1.")

    source_labels = split_source_tags(value)
    mapped: dict[str, list[str]] = {}
    dropped: dict[str, str] = {}
    unmapped: list[str] = []
    canonical: set[str] = set()

    for label in source_labels:
        outputs = TAG_ALIASES.get(label)
        if outputs is not None:
            mapped[label] = list(outputs)
            canonical.update(outputs)
            continue
        reason = _drop_reason(label)
        if reason is not None:
            dropped[label] = reason
            continue
        unmapped.append(label)

    suppressed: list[str] = []
    for redundant, stronger_tags in REDUNDANCY_RULES:
        if redundant in canonical and canonical.intersection(stronger_tags):
            canonical.remove(redundant)
            suppressed.append(redundant)

    ordered = sorted(canonical, key=TAG_PRIORITY.__getitem__)
    retained = ordered[:limit]
    capped = ordered[limit:]
    return TagNormalizationResult(
        source_labels=source_labels,
        tags=retained,
        mapped=mapped,
        dropped=dropped,
        unmapped=unmapped,
        suppressed=suppressed,
        capped=capped,
    )


def tags_to_string(tags: Iterable[str]) -> str:
    return "; ".join(tags)
