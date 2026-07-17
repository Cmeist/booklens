import type { BookLensData, BookLensDataSource } from "@/lib/booklens-data";
import { filterDisplayTopTags } from "@/lib/display-tags";
import type { Book, TopTag } from "@/lib/types";

export type CatalogSummary = {
  totalBooks: number;
  dataSourceLabel: string;
  topTags: TopTag[];
  ratingCoveragePercent: number;
  pageCountCoveragePercent: number;
  ratedCount: number;
  pageCountKnownCount: number;
};

export function dataSourceLabel(source: BookLensDataSource): string {
  return source === "supabase" ? "Supabase" : "Sample fixture";
}

function coveragePercent(known: number, total: number): number {
  if (total <= 0) {
    return 0;
  }
  return Math.round((known / total) * 100);
}

export function buildCatalogSummary(data: BookLensData): CatalogSummary {
  const { books, topTags, source } = data;
  const totalBooks = books.length;
  let ratedCount = 0;
  let pageCountKnownCount = 0;

  for (const book of books) {
    if (book.averageRating !== null) {
      ratedCount += 1;
    }
    if (book.pageCount !== null) {
      pageCountKnownCount += 1;
    }
  }

  return {
    totalBooks,
    dataSourceLabel: dataSourceLabel(source),
    topTags: filterDisplayTopTags(topTags).slice(0, 3),
    ratingCoveragePercent: coveragePercent(ratedCount, totalBooks),
    pageCountCoveragePercent: coveragePercent(pageCountKnownCount, totalBooks),
    ratedCount,
    pageCountKnownCount,
  };
}

/** Prefer highest community ratings; fall back to catalog order. */
export function selectFeaturedBooks(books: Book[], limit = 3): Book[] {
  const rated = books
    .filter((book) => book.averageRating !== null)
    .sort((left, right) => {
      const ratingDelta = (right.averageRating ?? 0) - (left.averageRating ?? 0);
      if (ratingDelta !== 0) {
        return ratingDelta;
      }
      return (right.ratingCount ?? 0) - (left.ratingCount ?? 0);
    });

  if (rated.length >= limit) {
    return rated.slice(0, limit);
  }

  const seen = new Set(rated.map((book) => book.id));
  const fillers = books.filter((book) => !seen.has(book.id));
  return [...rated, ...fillers].slice(0, limit);
}

export function formatPreferredLengthLabel(
  length: "short" | "medium" | "long" | "any",
): string {
  if (length === "any") {
    return "Any";
  }
  return length.charAt(0).toUpperCase() + length.slice(1);
}

export function formatCoverageLabel(percent: number, known: number, total: number): string {
  return `${percent}% (${known.toLocaleString()} / ${total.toLocaleString()})`;
}
