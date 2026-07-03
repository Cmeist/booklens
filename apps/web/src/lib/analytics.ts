import type { Book, TopTag } from "@/lib/types";

const MIN_RATED_BOOKS_PER_TAG = 2;
const MIN_POINTS_FOR_SCATTER = 2;

export type DecadeCount = {
  decade: string;
  count: number;
};

export type TagRatingAverage = {
  tag: string;
  bookCount: number;
  ratedBookCount: number;
  averageRating: number | null;
  hasEnoughRatingData: boolean;
};

export type RatedBookPoint = {
  id: string;
  title: string;
  pageCount: number | null;
  ratingCount: number | null;
  averageRating: number;
};

export type AnalyticsSnapshot = {
  bookCount: number;
  ratedBookCount: number;
  booksWithPageCount: number;
  booksWithRatingCount: number;
  booksWithDecade: number;
  averageRating: number | null;
  averagePageCount: number | null;
  topTags: TopTag[];
  decadeDistribution: DecadeCount[];
  averageRatingByTag: TagRatingAverage[];
  pageCountVsRating: RatedBookPoint[];
  ratingCountVsRating: RatedBookPoint[];
  canShowPageCountVsRating: boolean;
  canShowRatingCountVsRating: boolean;
  canShowAverageRatingByTag: boolean;
  canShowDecadeDistribution: boolean;
};

function average(values: number[]): number | null {
  if (values.length === 0) {
    return null;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
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

export function buildAverageRatingByTag(books: Book[]): TagRatingAverage[] {
  const tagStats = new Map<string, { bookCount: number; ratings: number[] }>();

  for (const book of books) {
    for (const tag of book.tags) {
      const current = tagStats.get(tag) ?? { bookCount: 0, ratings: [] };
      current.bookCount += 1;
      if (book.averageRating !== null) {
        current.ratings.push(book.averageRating);
      }
      tagStats.set(tag, current);
    }
  }

  return Array.from(tagStats.entries())
    .map(([tag, stats]) => {
      const ratedBookCount = stats.ratings.length;
      const hasEnoughRatingData = ratedBookCount >= MIN_RATED_BOOKS_PER_TAG;
      return {
        tag,
        bookCount: stats.bookCount,
        ratedBookCount,
        averageRating: hasEnoughRatingData ? average(stats.ratings) : null,
        hasEnoughRatingData,
      };
    })
    .sort((left, right) => {
      if (right.bookCount !== left.bookCount) {
        return right.bookCount - left.bookCount;
      }
      return left.tag.localeCompare(right.tag);
    });
}

function buildRatedBookPoints(
  books: Book[],
  requirePageCount: boolean,
  requireRatingCount: boolean,
): RatedBookPoint[] {
  return books
    .filter((book) => {
      if (book.averageRating === null) {
        return false;
      }
      if (requirePageCount && book.pageCount === null) {
        return false;
      }
      if (requireRatingCount && book.ratingCount === null) {
        return false;
      }
      return true;
    })
    .map((book) => ({
      id: book.id,
      title: book.title,
      pageCount: book.pageCount,
      ratingCount: book.ratingCount,
      averageRating: book.averageRating as number,
    }));
}

export function buildAnalyticsSnapshot(books: Book[], topTags: TopTag[]): AnalyticsSnapshot {
  const ratedBooks = books.filter((book) => book.averageRating !== null);
  const pageCounts = books
    .map((book) => book.pageCount)
    .filter((value): value is number => value !== null);
  const ratingCounts = books
    .map((book) => book.ratingCount)
    .filter((value): value is number => value !== null);

  const pageCountVsRating = buildRatedBookPoints(books, true, false);
  const ratingCountVsRating = buildRatedBookPoints(books, false, true);
  const averageRatingByTag = buildAverageRatingByTag(books);
  const decadeDistribution = buildDecadeDistribution(books);

  const tagsWithEnoughRatings = averageRatingByTag.filter((item) => item.hasEnoughRatingData);

  return {
    bookCount: books.length,
    ratedBookCount: ratedBooks.length,
    booksWithPageCount: pageCounts.length,
    booksWithRatingCount: ratingCounts.length,
    booksWithDecade: books.filter((book) => book.decade !== null).length,
    averageRating: average(ratedBooks.map((book) => book.averageRating as number)),
    averagePageCount:
      pageCounts.length > 0
        ? Math.round(pageCounts.reduce((sum, value) => sum + value, 0) / pageCounts.length)
        : null,
    topTags,
    decadeDistribution,
    averageRatingByTag,
    pageCountVsRating,
    ratingCountVsRating,
    canShowPageCountVsRating: pageCountVsRating.length >= MIN_POINTS_FOR_SCATTER,
    canShowRatingCountVsRating: ratingCountVsRating.length >= MIN_POINTS_FOR_SCATTER,
    canShowAverageRatingByTag: tagsWithEnoughRatings.length > 0,
    canShowDecadeDistribution: decadeDistribution.some((item) => item.decade !== "Unknown decade"),
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
