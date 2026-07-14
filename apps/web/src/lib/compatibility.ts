import { filterDisplayTags } from "./display-tags";
import { scoreThemeProfile, type ThemeDimensionId } from "./theme-profile";
import type { Book } from "./types";
import {
  deriveTaste,
  type DerivedTaste,
  type PreferredLength,
  type ReadingPace,
  type UserProfile,
} from "./user-profile";

export type CompatibilityDimensionId =
  | "overall"
  | "theme"
  | "tags"
  | "length"
  | "rating";

export type CompatibilityDimension = {
  id: CompatibilityDimensionId;
  label: string;
  score: number | null;
};

export type CompatibilityResult = {
  overall: number | null;
  dimensions: CompatibilityDimension[];
  reasons: string[];
  ready: boolean;
};

const LENGTH_RANGES: Record<Exclude<PreferredLength, "any">, [number, number]> = {
  short: [0, 249],
  medium: [250, 450],
  long: [451, 10_000],
};

const PACE_TO_LENGTH: Record<Exclude<ReadingPace, "any">, PreferredLength> = {
  fast: "short",
  moderate: "medium",
  slow: "long",
};

/** Explicit preferredLength wins; otherwise map Reading pace → length band. */
export function effectivePreferredLength(profile: UserProfile): PreferredLength {
  if (profile.preferences.preferredLength !== "any") {
    return profile.preferences.preferredLength;
  }
  const pace = profile.preferences.pace;
  if (pace !== "any") {
    return PACE_TO_LENGTH[pace];
  }
  return "any";
}

function cosineSimilarity(
  left: Map<ThemeDimensionId, number>,
  right: Map<ThemeDimensionId, number>,
): number {
  let dot = 0;
  let leftNorm = 0;
  let rightNorm = 0;
  for (const [id, leftValue] of left) {
    const rightValue = right.get(id) ?? 0;
    dot += leftValue * rightValue;
    leftNorm += leftValue * leftValue;
  }
  for (const rightValue of right.values()) {
    rightNorm += rightValue * rightValue;
  }
  if (leftNorm === 0 || rightNorm === 0) {
    return 0;
  }
  return dot / (Math.sqrt(leftNorm) * Math.sqrt(rightNorm));
}

function lengthFitScore(
  preferred: PreferredLength,
  pageCount: number | null,
): number | null {
  if (preferred === "any") {
    return null;
  }
  if (pageCount === null) {
    return null;
  }
  const [min, max] = LENGTH_RANGES[preferred];
  if (pageCount >= min && pageCount <= max) {
    return 95;
  }
  const mid = (min + max) / 2;
  const distance = Math.abs(pageCount - mid);
  return Math.max(20, Math.round(95 - distance / 8));
}

function ratingAlignmentScore(
  profile: UserProfile,
  book: Book,
  averagePersonalRating: number | null,
): number | null {
  const floor = profile.preferences.minCommunityRating;
  const community = book.averageRating;

  if (community === null && floor === null && averagePersonalRating === null) {
    return null;
  }

  let score = 70;
  if (floor !== null && community !== null) {
    score = community >= floor ? 90 : Math.max(15, Math.round(90 - (floor - community) * 25));
  } else if (averagePersonalRating !== null && community !== null) {
    const delta = Math.abs(community - averagePersonalRating);
    score = Math.max(25, Math.round(95 - delta * 20));
  } else if (floor !== null && community === null) {
    score = 45;
  }
  return score;
}

export function scoreCompatibility(
  profile: UserProfile,
  book: Book,
  books: Book[],
): CompatibilityResult {
  const taste = deriveTaste(profile, books);
  return scoreCompatibilityWithTaste(profile, book, taste);
}

export function scoreCompatibilityWithTaste(
  profile: UserProfile,
  book: Book,
  taste: DerivedTaste,
): CompatibilityResult {
  const preferredLength = effectivePreferredLength(profile);
  const hasSignal =
    taste.logCount > 0 ||
    profile.preferences.favoriteGenres.length > 0 ||
    preferredLength !== "any" ||
    profile.preferences.minCommunityRating !== null;

  if (!hasSignal) {
    return {
      overall: null,
      dimensions: [
        { id: "overall", label: "Overall fit", score: null },
        { id: "theme", label: "Theme overlap", score: null },
        { id: "tags", label: "Tag overlap", score: null },
        { id: "length", label: "Pace & length", score: null },
        { id: "rating", label: "Rating alignment", score: null },
      ],
      reasons: ["Log a few books or set preferences to unlock compatibility scoring."],
      ready: false,
    };
  }

  const userThemeMap = new Map(
    taste.themeScores.map((item) => [item.id, item.score] as const),
  );

  let bookThemes: ReturnType<typeof scoreThemeProfile> | null = null;
  const getBookThemes = () => {
    bookThemes ??= scoreThemeProfile(book);
    return bookThemes;
  };

  const themeScore = (() => {
    if (taste.logCount === 0) {
      return null;
    }
    const bookThemeMap = new Map(
      getBookThemes().map((item) => [item.id, item.score] as const),
    );
    return Math.round(cosineSimilarity(userThemeMap, bookThemeMap) * 100);
  })();

  const bookTags = new Set(filterDisplayTags(book.tags).map((tag) => tag.toLowerCase()));
  const preferenceTags = new Set(profile.preferences.favoriteGenres);
  const tasteTags = new Set(taste.topTags.map((item) => item.tag.toLowerCase()));
  const interestTags = new Set([...preferenceTags, ...tasteTags]);

  let tagScore: number | null = null;
  const sharedTags: string[] = [];
  if (interestTags.size > 0) {
    for (const tag of interestTags) {
      if (bookTags.has(tag)) {
        sharedTags.push(tag);
      }
    }
    tagScore = Math.min(
      100,
      Math.round((sharedTags.length / Math.min(6, interestTags.size)) * 100),
    );
  }

  const lengthScore = lengthFitScore(preferredLength, book.pageCount);
  const ratingScore = ratingAlignmentScore(
    profile,
    book,
    taste.averagePersonalRating,
  );

  const parts: { score: number; weight: number }[] = [];
  if (themeScore !== null) {
    parts.push({ score: themeScore, weight: 0.35 });
  }
  if (tagScore !== null) {
    parts.push({ score: tagScore, weight: 0.3 });
  }
  if (lengthScore !== null) {
    parts.push({ score: lengthScore, weight: 0.2 });
  }
  if (ratingScore !== null) {
    parts.push({ score: ratingScore, weight: 0.15 });
  }

  const weightSum = parts.reduce((sum, part) => sum + part.weight, 0);
  const overall =
    weightSum > 0
      ? Math.round(
          parts.reduce((sum, part) => sum + part.score * part.weight, 0) / weightSum,
        )
      : null;

  const reasons: string[] = [];
  if (sharedTags.length > 0) {
    reasons.push(`Shares tags you like: ${sharedTags.slice(0, 3).join(", ")}`);
  }
  if (themeScore !== null && themeScore >= 55) {
    const topBookThemes = getBookThemes()
      .filter((item) => item.score > 0)
      .slice(0, 2)
      .map((item) => item.label);
    if (topBookThemes.length > 0) {
      reasons.push(`Theme fit with your taste (${topBookThemes.join(", ")})`);
    }
  }
  if (lengthScore !== null && lengthScore >= 80 && preferredLength !== "any") {
    const fromPace =
      profile.preferences.preferredLength === "any" &&
      profile.preferences.pace !== "any";
    reasons.push(
      fromPace
        ? `Fits your ${profile.preferences.pace} pace (${preferredLength} length)`
        : `Matches your usual ${preferredLength} length`,
    );
  } else if (lengthScore !== null && lengthScore < 50 && preferredLength !== "any") {
    reasons.push(`Length differs from your usual ${preferredLength} books`);
  }
  if (
    ratingScore !== null &&
    profile.preferences.minCommunityRating !== null &&
    book.averageRating !== null &&
    book.averageRating < profile.preferences.minCommunityRating
  ) {
    reasons.push(
      `Community rating below your floor (${profile.preferences.minCommunityRating})`,
    );
  }
  if (reasons.length === 0 && overall !== null) {
    reasons.push("Partial signal from your profile — log more rated books to sharpen this.");
  }

  return {
    overall,
    dimensions: [
      { id: "overall", label: "Overall fit", score: overall },
      { id: "theme", label: "Theme overlap", score: themeScore },
      { id: "tags", label: "Tag overlap", score: tagScore },
      { id: "length", label: "Pace & length", score: lengthScore },
      { id: "rating", label: "Rating alignment", score: ratingScore },
    ],
    reasons,
    ready: true,
  };
}
