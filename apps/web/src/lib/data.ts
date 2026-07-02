import booksData from "@/data/books.sample.json";
import recommendationsData from "@/data/recommendations.sample.json";
import topTagsData from "@/data/top-tags.sample.json";

import type { Book, BookRecommendation, RecommendationWithBook, TopTag } from "./types";

export const books = booksData as Book[];
export const topTags = topTagsData as TopTag[];
export const recommendations = recommendationsData as BookRecommendation[];

export function getBookById(id: string): Book | undefined {
  return books.find((book) => book.id === id);
}

export function getRecommendationsForBook(bookId: string): BookRecommendation[] {
  return recommendations.filter((item) => item.bookId === bookId);
}

export function getRecommendationsWithBooks(bookId: string): RecommendationWithBook[] {
  return getRecommendationsForBook(bookId).flatMap((recommendation) => {
    const book = getBookById(recommendation.similarBookId);
    if (!book) {
      return [];
    }
    return [{ recommendation, book }];
  });
}
