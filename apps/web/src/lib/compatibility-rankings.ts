import {
  effectivePreferredLength,
  scoreCompatibilityWithTaste,
  type CompatibilityResult,
} from "@/lib/compatibility";
import type { Book } from "@/lib/types";
import {
  deriveTaste,
  getLogEntry,
  type DerivedTaste,
  type UserProfile,
} from "@/lib/user-profile";

export type RankedCompatibilityItem = {
  book: Book;
  result: CompatibilityResult;
};

export type CompatibilityRankSort = "match" | "title" | "recent";

export type RankCompatibilityOptions = {
  hideRead?: boolean;
  query?: string;
  sort?: CompatibilityRankSort;
  limit?: number;
  derivedTaste?: DerivedTaste;
};

export function profileHasCompatibilitySignal(
  profile: UserProfile,
  books: Book[],
  derivedTaste?: DerivedTaste,
): boolean {
  const taste = derivedTaste ?? deriveTaste(profile, books);
  const preferredLength = effectivePreferredLength(profile);
  return (
    taste.logCount > 0 ||
    profile.preferences.favoriteGenres.length > 0 ||
    preferredLength !== "any" ||
    profile.preferences.minCommunityRating !== null
  );
}

function compareScores(
  left: RankedCompatibilityItem,
  right: RankedCompatibilityItem,
): number {
  const leftScore = left.result.overall;
  const rightScore = right.result.overall;
  if (leftScore === null && rightScore === null) {
    return left.book.title.localeCompare(right.book.title);
  }
  if (leftScore === null) {
    return 1;
  }
  if (rightScore === null) {
    return -1;
  }
  if (rightScore !== leftScore) {
    return rightScore - leftScore;
  }
  return left.book.title.localeCompare(right.book.title);
}

function logUpdatedAt(profile: UserProfile, bookId: string): string | null {
  return getLogEntry(profile, bookId)?.updatedAt ?? null;
}

/**
 * Rank catalog books for a local profile.
 * Null overall scores sink to the bottom; partial results stay visible.
 */
export function rankCompatibilityMatches(
  profile: UserProfile,
  books: Book[],
  options: RankCompatibilityOptions = {},
): RankedCompatibilityItem[] {
  const {
    hideRead = false,
    query = "",
    sort = "match",
    limit = 25,
    derivedTaste,
  } = options;

  const normalizedQuery = query.trim().toLowerCase();
  const taste = derivedTaste ?? deriveTaste(profile, books);

  const ranked: RankedCompatibilityItem[] = [];
  for (const book of books) {
    if (hideRead) {
      const entry = getLogEntry(profile, book.id);
      if (entry?.status === "read") {
        continue;
      }
    }

    if (normalizedQuery) {
      const haystack = `${book.title} ${book.author}`.toLowerCase();
      if (!haystack.includes(normalizedQuery)) {
        continue;
      }
    }

    ranked.push({
      book,
      result: scoreCompatibilityWithTaste(profile, book, taste),
    });
  }

  if (sort === "title") {
    ranked.sort((left, right) => left.book.title.localeCompare(right.book.title));
  } else if (sort === "recent") {
    ranked.sort((left, right) => {
      const leftAt = logUpdatedAt(profile, left.book.id);
      const rightAt = logUpdatedAt(profile, right.book.id);
      if (leftAt && rightAt && leftAt !== rightAt) {
        return rightAt.localeCompare(leftAt);
      }
      if (leftAt && !rightAt) {
        return -1;
      }
      if (!leftAt && rightAt) {
        return 1;
      }
      return compareScores(left, right);
    });
  } else {
    ranked.sort(compareScores);
  }

  if (limit > 0 && ranked.length > limit) {
    return ranked.slice(0, limit);
  }
  return ranked;
}

export function formatCompatibilityPercent(score: number | null): string {
  if (score === null) {
    return "Needs more signal";
  }
  return `${score}%`;
}

export function isPartialCompatibility(result: CompatibilityResult): boolean {
  if (!result.ready) {
    return false;
  }
  return result.dimensions.some(
    (dimension) => dimension.id !== "overall" && dimension.score === null,
  );
}
