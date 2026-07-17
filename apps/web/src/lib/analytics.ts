import type { Book, BookRecommendation } from "@/lib/types";

const MIN_POINTS_FOR_SCATTER = 2;
const MAX_SCATTER_POINTS = 40;
const MAX_REASON_ENTRIES = 6;
const MAX_HIDDEN_GEMS = 5;
const HIDDEN_GEM_MIN_RATING_COUNT = 3;
const HIDDEN_GEM_MIN_AVERAGE_RATING = 4.0;

export type DecadeCount = {
  decade: string;
  count: number;
};

export type CoverageMetric = {
  known: number;
  total: number;
  percent: number;
};

export type CatalogCoverage = {
  rating: CoverageMetric;
  pageCount: CoverageMetric;
  publicationYear: CoverageMetric;
  cover: CoverageMetric;
};

export type ReasonFrequency = {
  reason: string;
  count: number;
};

export type HiddenGem = {
  id: string;
  title: string;
  averageRating: number;
  ratingCount: number;
};

export type RatedBookPoint = {
  id: string;
  title: string;
  ratingCount: number;
  averageRating: number;
};

export type ScatterSeries = {
  points: RatedBookPoint[];
  totalEligible: number;
  isCapped: boolean;
};

export type AnalyticsSnapshot = {
  bookCount: number;
  coverage: CatalogCoverage;
  decadeDistribution: DecadeCount[];
  canShowDecadeDistribution: boolean;
  ratingCountVsRating: ScatterSeries;
  canShowRatingCountVsRating: boolean;
  recommendationCoverage: CoverageMetric;
  reasonFrequency: ReasonFrequency[];
  canShowReasonFrequency: boolean;
  hiddenGems: HiddenGem[];
  canShowHiddenGems: boolean;
};

function coveragePercent(known: number, total: number): number {
  if (total <= 0) {
    return 0;
  }
  return Math.round((known / total) * 100);
}

function coverageMetric(known: number, total: number): CoverageMetric {
  return {
    known,
    total,
    percent: coveragePercent(known, total),
  };
}

export function buildCatalogCoverage(books: Book[]): CatalogCoverage {
  const total = books.length;
  let ratingKnown = 0;
  let pageCountKnown = 0;
  let publicationYearKnown = 0;
  let coverKnown = 0;

  for (const book of books) {
    if (book.averageRating !== null) {
      ratingKnown += 1;
    }
    if (book.pageCount !== null) {
      pageCountKnown += 1;
    }
    if (book.publicationYear !== null) {
      publicationYearKnown += 1;
    }
    if (book.coverUrl !== null && book.coverUrl.trim() !== "") {
      coverKnown += 1;
    }
  }

  return {
    rating: coverageMetric(ratingKnown, total),
    pageCount: coverageMetric(pageCountKnown, total),
    publicationYear: coverageMetric(publicationYearKnown, total),
    cover: coverageMetric(coverKnown, total),
  };
}

export function buildDecadeDistribution(books: Book[]): DecadeCount[] {
  const counts = new Map<string, number>();

  for (const book of books) {
    const label = book.decade ?? "Unknown decade";
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }

  return Array.from(counts.entries())
    .map(([decade, count]) => ({ decade, count }))
    .sort((left, right) => left.decade.localeCompare(right.decade));
}

export function filterValidRecommendations(
  books: Book[],
  recommendations: BookRecommendation[],
): BookRecommendation[] {
  const bookIds = new Set(books.map((book) => book.id));

  return recommendations.filter(
    (recommendation) =>
      bookIds.has(recommendation.bookId) &&
      bookIds.has(recommendation.similarBookId) &&
      recommendation.bookId !== recommendation.similarBookId,
  );
}

export function buildRecommendationCoverage(
  books: Book[],
  validRecommendations: BookRecommendation[],
): CoverageMetric {
  const sources = new Set(validRecommendations.map((recommendation) => recommendation.bookId));
  return coverageMetric(sources.size, books.length);
}

export function buildReasonFrequency(
  validRecommendations: BookRecommendation[],
): ReasonFrequency[] {
  const counts = new Map<string, number>();

  for (const recommendation of validRecommendations) {
    const uniqueReasons = new Set(
      recommendation.reasons.map((reason) => reason.trim()).filter((reason) => reason.length > 0),
    );

    for (const reason of uniqueReasons) {
      counts.set(reason, (counts.get(reason) ?? 0) + 1);
    }
  }

  return Array.from(counts.entries())
    .map(([reason, count]) => ({ reason, count }))
    .sort((left, right) => {
      if (right.count !== left.count) {
        return right.count - left.count;
      }
      return left.reason.localeCompare(right.reason);
    })
    .slice(0, MAX_REASON_ENTRIES);
}

function median(values: number[]): number | null {
  if (values.length === 0) {
    return null;
  }

  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);

  if (sorted.length % 2 === 1) {
    return sorted[middle];
  }

  return (sorted[middle - 1] + sorted[middle]) / 2;
}

export function buildHiddenGems(books: Book[]): HiddenGem[] {
  const eligible = books.filter(
    (book) =>
      book.averageRating !== null &&
      book.ratingCount !== null &&
      book.ratingCount >= HIDDEN_GEM_MIN_RATING_COUNT,
  );

  const ratingCountMedian = median(eligible.map((book) => book.ratingCount as number));
  if (ratingCountMedian === null) {
    return [];
  }

  return eligible
    .filter(
      (book) =>
        (book.ratingCount as number) <= ratingCountMedian &&
        (book.averageRating as number) >= HIDDEN_GEM_MIN_AVERAGE_RATING,
    )
    .map((book) => ({
      id: book.id,
      title: book.title,
      averageRating: book.averageRating as number,
      ratingCount: book.ratingCount as number,
    }))
    .sort((left, right) => {
      if (right.averageRating !== left.averageRating) {
        return right.averageRating - left.averageRating;
      }
      if (left.ratingCount !== right.ratingCount) {
        return left.ratingCount - right.ratingCount;
      }
      const titleDelta = left.title.localeCompare(right.title);
      if (titleDelta !== 0) {
        return titleDelta;
      }
      return left.id.localeCompare(right.id);
    })
    .slice(0, MAX_HIDDEN_GEMS);
}

export function buildRatingCountScatter(books: Book[]): ScatterSeries {
  const eligible = books
    .filter((book) => book.averageRating !== null && book.ratingCount !== null)
    .map((book) => ({
      id: book.id,
      title: book.title,
      ratingCount: book.ratingCount as number,
      averageRating: book.averageRating as number,
    }))
    .sort((left, right) => {
      if (right.ratingCount !== left.ratingCount) {
        return right.ratingCount - left.ratingCount;
      }
      const titleDelta = left.title.localeCompare(right.title);
      if (titleDelta !== 0) {
        return titleDelta;
      }
      return left.id.localeCompare(right.id);
    });

  const totalEligible = eligible.length;
  const points = eligible.slice(0, MAX_SCATTER_POINTS);

  return {
    points,
    totalEligible,
    isCapped: totalEligible > MAX_SCATTER_POINTS,
  };
}

export function buildAnalyticsSnapshot(
  books: Book[],
  recommendations: BookRecommendation[],
): AnalyticsSnapshot {
  const decadeDistribution = buildDecadeDistribution(books);
  const validRecommendations = filterValidRecommendations(books, recommendations);
  const reasonFrequency = buildReasonFrequency(validRecommendations);
  const ratingCountVsRating = buildRatingCountScatter(books);
  const hiddenGems = buildHiddenGems(books);

  return {
    bookCount: books.length,
    coverage: buildCatalogCoverage(books),
    decadeDistribution,
    canShowDecadeDistribution: decadeDistribution.some((item) => item.decade !== "Unknown decade"),
    ratingCountVsRating,
    canShowRatingCountVsRating: ratingCountVsRating.totalEligible >= MIN_POINTS_FOR_SCATTER,
    recommendationCoverage: buildRecommendationCoverage(books, validRecommendations),
    reasonFrequency,
    canShowReasonFrequency: reasonFrequency.length > 0,
    hiddenGems,
    canShowHiddenGems: hiddenGems.length > 0,
  };
}

export function normalizeScatterX(value: number, min: number, max: number): number {
  if (max === min) {
    return 50;
  }
  return ((value - min) / (max - min)) * 100;
}

export function normalizeScatterY(value: number, min: number, max: number): number {
  if (max === min) {
    return 50;
  }
  return 100 - ((value - min) / (max - min)) * 100;
}
