import type { Book, BookRecommendation, TopTag } from "@/lib/types";

export type BooksWithTagsRow = {
  id: string;
  title: string;
  author: string;
  description: string | null;
  publication_year: number | null;
  decade: string | null;
  page_count: number | null;
  rating_count: number | null;
  average_rating: number | string | null;
  cover_url: string | null;
  source: string;
  source_id: string;
  tags: string[] | null;
};

export type TopTagsRow = {
  tag: string;
  book_count: number;
};

export type BookRecommendationsRow = {
  book_id: string;
  similar_book_id: string;
  score: number | string;
  reasons: string[] | null;
};

function toNumber(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function mapBookRow(row: BooksWithTagsRow): Book {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    description: row.description ?? "",
    tags: row.tags ?? [],
    publicationYear: row.publication_year,
    decade: row.decade,
    pageCount: row.page_count,
    ratingCount: row.rating_count,
    averageRating: toNumber(row.average_rating),
    coverUrl: row.cover_url,
    source: row.source,
    sourceId: row.source_id,
  };
}

export function mapTopTagRow(row: TopTagsRow): TopTag {
  return {
    tag: row.tag,
    bookCount: row.book_count,
  };
}

export function mapRecommendationRow(row: BookRecommendationsRow): BookRecommendation {
  return {
    bookId: row.book_id,
    similarBookId: row.similar_book_id,
    score: toNumber(row.score) ?? 0,
    reasons: row.reasons ?? [],
  };
}
