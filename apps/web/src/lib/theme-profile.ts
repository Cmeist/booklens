import { filterDisplayTags } from "./display-tags";
import type { Book } from "./types";

export type ThemeDimensionId =
  | "romance"
  | "politics"
  | "action"
  | "mystery"
  | "suspense"
  | "fantasy"
  | "science"
  | "horror"
  | "family"
  | "comingOfAge"
  | "social"
  | "humor";

export type ThemeDimension = {
  id: ThemeDimensionId;
  label: string;
};

export type ThemeScore = {
  id: ThemeDimensionId;
  label: string;
  score: number;
};

/** Raw points needed to map to 100%. Strong multi-signal books can hit the ceiling. */
const RAW_CAP = 14;

const TAG_HIT = 3;
const TITLE_HIT = 2;
const DESCRIPTION_HIT = 1;
const DESCRIPTION_HIT_CAP_PER_KEYWORD = 3;

export const THEME_DIMENSIONS: ThemeDimension[] = [
  { id: "romance", label: "Romance" },
  { id: "politics", label: "Politics / Power" },
  { id: "action", label: "Action / Adventure" },
  { id: "mystery", label: "Mystery / Investigation" },
  { id: "suspense", label: "Suspense / Thriller" },
  { id: "fantasy", label: "Fantasy / Magic" },
  { id: "science", label: "Science / Technology" },
  { id: "horror", label: "Horror / Darkness" },
  { id: "family", label: "Family / Friendship" },
  { id: "comingOfAge", label: "Coming of Age" },
  { id: "social", label: "Social Issues / Class" },
  { id: "humor", label: "Humor / Satire" },
];

/**
 * Keyword/phrase lexicon per theme.
 * Prefer multi-word phrases that match OL subjects; single words for title/description.
 */
export const THEME_LEXICON: Record<ThemeDimensionId, string[]> = {
  romance: [
    "romance",
    "love stories",
    "love story",
    "romantic",
    "marriage",
    "courtship",
    "heartbreak",
    "attraction",
    "lovers",
    "dating",
    "weddings",
    "relationships",
    "man-woman relationships",
  ],
  politics: [
    "politics",
    "political",
    "government",
    "war",
    "warfare",
    "military",
    "leadership",
    "corruption",
    "empire",
    "revolution",
    "diplomacy",
    "power",
    "dictatorship",
    "kings and rulers",
    "political science",
    "strategy",
  ],
  action: [
    "action",
    "adventure",
    "quest",
    "quests",
    "survival",
    "battle",
    "battles",
    "danger",
    "expedition",
    "voyage",
    "voyages",
    "treasure",
    "chase",
    "action & adventure",
    "adventure stories",
  ],
  mystery: [
    "mystery",
    "detective",
    "detectives",
    "investigation",
    "clues",
    "puzzle",
    "puzzles",
    "crime",
    "murder",
    "whodunit",
    "private investigators",
    "mystery & detective",
    "detective and mystery",
    "secrets",
  ],
  suspense: [
    "suspense",
    "thriller",
    "thrillers",
    "paranoia",
    "high stakes",
    "tension",
    "espionage",
    "spy",
    "spies",
    "conspiracy",
    "chase",
    "psychological thriller",
  ],
  fantasy: [
    "fantasy",
    "magic",
    "magical",
    "wizard",
    "wizards",
    "witch",
    "witches",
    "dragon",
    "dragons",
    "mythical",
    "mythology",
    "fairy tales",
    "fairy tale",
    "enchanted",
    "sorcery",
    "imaginary places",
    "fantasy fiction",
  ],
  science: [
    "science fiction",
    "sci-fi",
    "scifi",
    "space",
    "spaceship",
    "artificial intelligence",
    "ai",
    "robot",
    "robots",
    "technology",
    "futuristic",
    "cyberpunk",
    "dystopia",
    "dystopian",
    "invention",
    "inventions",
    "time travel",
    "extraterrestrial",
  ],
  horror: [
    "horror",
    "gothic",
    "monster",
    "monsters",
    "vampire",
    "vampires",
    "ghost",
    "ghosts",
    "dread",
    "terror",
    "supernatural",
    "psychological horror",
    "darkness",
    "violence",
    "haunted",
    "zombie",
    "zombies",
  ],
  family: [
    "family",
    "families",
    "friendship",
    "friends",
    "loyalty",
    "found family",
    "siblings",
    "parents",
    "motherhood",
    "fatherhood",
    "domestic",
    "family life",
    "brothers",
    "sisters",
  ],
  comingOfAge: [
    "coming of age",
    "bildungsroman",
    "growing up",
    "adolescence",
    "teenagers",
    "young adult",
    "self-discovery",
    "identity",
    "school",
    "boarding school",
    "maturity",
    "juvenile fiction",
    "children's fiction",
  ],
  social: [
    "social issues",
    "social conditions",
    "class",
    "inequality",
    "poverty",
    "racism",
    "race relations",
    "gender",
    "justice",
    "civil rights",
    "feminism",
    "oppression",
    "working class",
    "slavery",
    "discrimination",
    "social justice",
  ],
  humor: [
    "humor",
    "humour",
    "comedy",
    "satire",
    "satirical",
    "wit",
    "witty",
    "parody",
    "absurd",
    "absurdity",
    "funny",
    "humorous",
    "comic",
    "irony",
  ],
};

function normalize(text: string): string {
  return text.toLowerCase().replace(/[_/]+/g, " ").replace(/\s+/g, " ").trim();
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Word-boundary pattern so "class" ≠ "classical", "spy" ≠ "conspiracy". */
function keywordPattern(needle: string): RegExp {
  const parts = needle.split(/\s+/).map(escapeRegExp);
  return new RegExp(`(?:^|[^a-z0-9])${parts.join("[^a-z0-9]+")}(?:[^a-z0-9]|$)`, "g");
}

function countOccurrences(haystack: string, needle: string): number {
  if (!needle || !haystack) {
    return 0;
  }
  return (haystack.match(keywordPattern(needle)) ?? []).length;
}

function textIncludesKeyword(haystack: string, needle: string): boolean {
  return countOccurrences(haystack, needle) > 0;
}

function tagMatchesKeyword(tag: string, keyword: string): boolean {
  if (tag === keyword) {
    return true;
  }
  return textIncludesKeyword(tag, keyword);
}

function scoreDimension(
  keywords: string[],
  tags: string[],
  title: string,
  description: string,
): number {
  let raw = 0;

  for (const keyword of keywords) {
    const needle = normalize(keyword);
    if (!needle) {
      continue;
    }

    if (tags.some((tag) => tagMatchesKeyword(tag, needle))) {
      raw += TAG_HIT;
    }

    if (textIncludesKeyword(title, needle)) {
      raw += TITLE_HIT;
    }

    const descHits = Math.min(
      DESCRIPTION_HIT_CAP_PER_KEYWORD,
      countOccurrences(description, needle),
    );
    raw += descHits * DESCRIPTION_HIT;
  }

  return Math.min(100, Math.round((100 * raw) / RAW_CAP));
}

export function scoreThemeProfile(book: Book): ThemeScore[] {
  const title = normalize(book.title);
  const description = normalize(book.description);
  const tags = filterDisplayTags(book.tags).map(normalize);

  const order = new Map(THEME_DIMENSIONS.map((dim, index) => [dim.id, index]));

  const scores: ThemeScore[] = THEME_DIMENSIONS.map((dim) => ({
    id: dim.id,
    label: dim.label,
    score: scoreDimension(THEME_LEXICON[dim.id], tags, title, description),
  }));

  return scores.sort((left, right) => {
    if (right.score !== left.score) {
      return right.score - left.score;
    }
    return (order.get(left.id) ?? 0) - (order.get(right.id) ?? 0);
  });
}

export function selectThemeScoresForDisplay(
  scores: ThemeScore[],
  maxRows?: number,
): ThemeScore[] {
  if (maxRows === undefined) {
    return scores;
  }

  const positive = scores.filter((item) => item.score > 0);
  const pool = positive.length > 0 ? positive : scores;
  return pool.slice(0, maxRows);
}
