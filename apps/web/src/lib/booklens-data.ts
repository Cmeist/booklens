import booksData from "@/data/books.sample.json";
import recommendationsData from "@/data/recommendations.sample.json";
import topTagsData from "@/data/top-tags.sample.json";

import type { Book, BookRecommendation, RecommendationWithBook, TopTag } from "./types";

export type BookLensDataSource = "supabase" | "fixture";

export type BookLensData = {
  source: BookLensDataSource;
  books: Book[];
  topTags: TopTag[];
  recommendations: BookRecommendation[];
};

export function sortTopTags(topTags: TopTag[]): TopTag[] {
  return [...topTags].sort((left, right) => {
    if (right.bookCount !== left.bookCount) {
      return right.bookCount - left.bookCount;
    }
    return left.tag.localeCompare(right.tag);
  });
}

export function sortRecommendations(
  recommendations: BookRecommendation[],
): BookRecommendation[] {
  return [...recommendations].sort((left, right) => {
    if (left.bookId !== right.bookId) {
      return left.bookId.localeCompare(right.bookId);
    }
    return right.score - left.score;
  });
}

export function loadFixtureData(): BookLensData {
  return {
    source: "fixture",
    books: booksData as Book[],
    topTags: sortTopTags(topTagsData as TopTag[]),
    recommendations: sortRecommendations(recommendationsData as BookRecommendation[]),
  };
}

export function getBookById(books: Book[], id: string): Book | undefined {
  return books.find((book) => book.id === id);
}

export function getRecommendationsForBook(
  recommendations: BookRecommendation[],
  bookId: string,
): BookRecommendation[] {
  return recommendations
    .filter((item) => item.bookId === bookId)
    .sort((left, right) => right.score - left.score);
}

export function getRecommendationsWithBooks(
  books: Book[],
  recommendations: BookRecommendation[],
  bookId: string,
): RecommendationWithBook[] {
  return getRecommendationsForBook(recommendations, bookId).flatMap((recommendation) => {
    const book = getBookById(books, recommendation.similarBookId);
    if (!book) {
      return [];
    }
    return [{ recommendation, book }];
  });
}
