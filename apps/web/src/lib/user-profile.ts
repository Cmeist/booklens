import { filterDisplayTags } from "./display-tags";
import {
  scoreThemeProfile,
  THEME_DIMENSIONS,
  type ThemeDimensionId,
  type ThemeScore,
} from "./theme-profile";
import type { Book } from "./types";

export const USER_PROFILE_STORAGE_KEY = "booklens.userProfile.v1";

export type LogStatus = "want" | "reading" | "read";

export type ReadingLogEntry = {
  bookId: string;
  status: LogStatus;
  rating: number | null;
  note: string;
  updatedAt: string;
};

export type PreferredLength = "short" | "medium" | "long" | "any";
export type ReadingPace = "fast" | "moderate" | "slow" | "any";

export type UserPreferences = {
  favoriteGenres: string[];
  preferredLength: PreferredLength;
  minCommunityRating: number | null;
  pace: ReadingPace;
};

export type UserProfile = {
  version: 1;
  preferences: UserPreferences;
  log: ReadingLogEntry[];
};

export type DerivedTaste = {
  topTags: { tag: string; weight: number }[];
  themeScores: ThemeScore[];
  preferredLength: PreferredLength;
  averagePersonalRating: number | null;
  ratedCount: number;
  logCount: number;
};

export const defaultUserPreferences: UserPreferences = {
  favoriteGenres: [],
  preferredLength: "any",
  minCommunityRating: null,
  pace: "any",
};

export const defaultUserProfile: UserProfile = {
  version: 1,
  preferences: { ...defaultUserPreferences },
  log: [],
};

export const LOG_STATUS_LABELS: Record<LogStatus, string> = {
  want: "Want to read",
  reading: "Reading",
  read: "Read",
};

/** Personal ratings: 0.5–5 in half-star steps. */
export const RATING_STEPS: number[] = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5];

export function clampRating(value: number | null): number | null {
  if (value === null || Number.isNaN(value)) {
    return null;
  }
  const half = Math.round(value * 2) / 2;
  if (half < 0.5 || half > 5) {
    return null;
  }
  return half;
}

export function formatPersonalRating(rating: number | null): string {
  if (rating === null) {
    return "";
  }
  return Number.isInteger(rating) ? `${rating}★` : `${rating.toFixed(1)}★`;
}

function parseFavoriteGenres(raw: unknown): string[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  const genres: string[] = [];
  const seen = new Set<string>();
  for (const item of raw) {
    if (typeof item !== "string") {
      continue;
    }
    const tag = item.trim().toLowerCase();
    if (!tag || seen.has(tag)) {
      continue;
    }
    seen.add(tag);
    genres.push(tag);
  }
  return genres;
}

export function createEmptyProfile(): UserProfile {
  return {
    version: 1,
    preferences: { ...defaultUserPreferences, favoriteGenres: [] },
    log: [],
  };
}

export function normalizeUserProfile(raw: unknown): UserProfile {
  if (!raw || typeof raw !== "object") {
    return createEmptyProfile();
  }

  const data = raw as Partial<UserProfile>;
  const preferencesRaw =
    data.preferences && typeof data.preferences === "object"
      ? data.preferences
      : defaultUserPreferences;

  const preferredLength = (
    ["short", "medium", "long", "any"] as PreferredLength[]
  ).includes(preferencesRaw.preferredLength as PreferredLength)
    ? (preferencesRaw.preferredLength as PreferredLength)
    : "any";

  const pace = (["fast", "moderate", "slow", "any"] as ReadingPace[]).includes(
    preferencesRaw.pace as ReadingPace,
  )
    ? (preferencesRaw.pace as ReadingPace)
    : "any";

  const minCommunityRating =
    typeof preferencesRaw.minCommunityRating === "number" &&
    Number.isFinite(preferencesRaw.minCommunityRating)
      ? Math.min(5, Math.max(0, preferencesRaw.minCommunityRating))
      : null;

  const log: ReadingLogEntry[] = [];
  if (Array.isArray(data.log)) {
    for (const item of data.log) {
      if (!item || typeof item !== "object") {
        continue;
      }
      const entry = item as Partial<ReadingLogEntry>;
      if (typeof entry.bookId !== "string" || !entry.bookId.trim()) {
        continue;
      }
      const status = (["want", "reading", "read"] as LogStatus[]).includes(
        entry.status as LogStatus,
      )
        ? (entry.status as LogStatus)
        : "want";
      log.push({
        bookId: entry.bookId,
        status,
        rating: clampRating(typeof entry.rating === "number" ? entry.rating : null),
        note: typeof entry.note === "string" ? entry.note.slice(0, 280) : "",
        updatedAt:
          typeof entry.updatedAt === "string" && entry.updatedAt
            ? entry.updatedAt
            : new Date().toISOString(),
      });
    }
  }

  return {
    version: 1,
    preferences: {
      favoriteGenres: parseFavoriteGenres(preferencesRaw.favoriteGenres),
      preferredLength,
      minCommunityRating,
      pace,
    },
    log,
  };
}

export function loadUserProfile(): UserProfile {
  if (typeof window === "undefined") {
    return createEmptyProfile();
  }
  try {
    const raw = window.localStorage.getItem(USER_PROFILE_STORAGE_KEY);
    if (!raw) {
      return createEmptyProfile();
    }
    return normalizeUserProfile(JSON.parse(raw));
  } catch {
    return createEmptyProfile();
  }
}

export function saveUserProfile(profile: UserProfile): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(
    USER_PROFILE_STORAGE_KEY,
    JSON.stringify(normalizeUserProfile(profile)),
  );
}

export function getLogEntry(
  profile: UserProfile,
  bookId: string,
): ReadingLogEntry | undefined {
  return profile.log.find((entry) => entry.bookId === bookId);
}

export function upsertLogEntry(
  profile: UserProfile,
  patch: {
    bookId: string;
    status?: LogStatus;
    rating?: number | null;
    note?: string;
  },
): UserProfile {
  const existing = getLogEntry(profile, patch.bookId);
  const nextEntry: ReadingLogEntry = {
    bookId: patch.bookId,
    status: patch.status ?? existing?.status ?? "want",
    rating:
      patch.rating !== undefined
        ? clampRating(patch.rating)
        : (existing?.rating ?? null),
    note: patch.note !== undefined ? patch.note.slice(0, 280) : (existing?.note ?? ""),
    updatedAt: new Date().toISOString(),
  };

  const log = existing
    ? profile.log.map((entry) => (entry.bookId === patch.bookId ? nextEntry : entry))
    : [nextEntry, ...profile.log];

  return { ...profile, log };
}

export function removeLogEntry(profile: UserProfile, bookId: string): UserProfile {
  return {
    ...profile,
    log: profile.log.filter((entry) => entry.bookId !== bookId),
  };
}

export function updatePreferences(
  profile: UserProfile,
  preferences: Partial<UserPreferences>,
): UserProfile {
  return {
    ...profile,
    preferences: normalizeUserProfile({
      ...profile,
      preferences: { ...profile.preferences, ...preferences },
    }).preferences,
  };
}

function lengthBand(pageCount: number | null): PreferredLength {
  if (pageCount === null) {
    return "any";
  }
  if (pageCount < 250) {
    return "short";
  }
  if (pageCount <= 450) {
    return "medium";
  }
  return "long";
}

function ratingWeight(rating: number | null): number {
  if (rating === null) {
    return 1;
  }
  return Math.max(0.5, rating);
}

export function deriveTaste(profile: UserProfile, books: Book[]): DerivedTaste {
  const bookById = new Map(books.map((book) => [book.id, book]));
  const tagWeights = new Map<string, number>();
  const themeTotals = new Map<ThemeDimensionId, { sum: number; weight: number }>();
  const lengthVotes = new Map<PreferredLength, number>();
  let ratingSum = 0;
  let ratedCount = 0;

  for (const entry of profile.log) {
    const book = bookById.get(entry.bookId);
    if (!book) {
      continue;
    }
    const weight = ratingWeight(entry.rating);
    if (entry.rating !== null) {
      ratingSum += entry.rating;
      ratedCount += 1;
    }

    for (const tag of filterDisplayTags(book.tags)) {
      tagWeights.set(tag, (tagWeights.get(tag) ?? 0) + weight);
    }

    for (const theme of scoreThemeProfile(book)) {
      const current = themeTotals.get(theme.id) ?? { sum: 0, weight: 0 };
      current.sum += theme.score * weight;
      current.weight += weight;
      themeTotals.set(theme.id, current);
    }

    const band = lengthBand(book.pageCount);
    if (band !== "any") {
      lengthVotes.set(band, (lengthVotes.get(band) ?? 0) + weight);
    }
  }

  const topTags = [...tagWeights.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .slice(0, 8)
    .map(([tag, weight]) => ({ tag, weight: Math.round(weight * 10) / 10 }));

  const themeScores: ThemeScore[] = THEME_DIMENSIONS.map((dim) => {
    const totals = themeTotals.get(dim.id);
    const score =
      totals && totals.weight > 0
        ? Math.round(totals.sum / totals.weight)
        : 0;
    return { id: dim.id, label: dim.label, score };
  }).sort((left, right) => right.score - left.score);

  let preferredLength: PreferredLength = profile.preferences.preferredLength;
  if (preferredLength === "any" && lengthVotes.size > 0) {
    preferredLength = [...lengthVotes.entries()].sort(
      (left, right) => right[1] - left[1],
    )[0][0];
  }

  return {
    topTags,
    themeScores,
    preferredLength,
    averagePersonalRating:
      ratedCount > 0 ? Math.round((ratingSum / ratedCount) * 10) / 10 : null,
    ratedCount,
    logCount: profile.log.length,
  };
}

export function parseGenresInput(value: string): string[] {
  return parseFavoriteGenres(
    value
      .split(/[,;]/)
      .map((part) => part.trim())
      .filter(Boolean),
  );
}
