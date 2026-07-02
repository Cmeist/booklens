export type Book = {
  id: string;
  title: string;
  author: string;
  description: string;
  tags: string[];
  publicationYear: number | null;
  decade: string | null;
  pageCount: number | null;
  ratingCount: number | null;
  averageRating: number | null;
  coverUrl: string | null;
  source: string;
  sourceId: string;
};

export type TopTag = {
  tag: string;
  bookCount: number;
};

export type BookRecommendation = {
  bookId: string;
  similarBookId: string;
  score: number;
  reasons: string[];
};

export type RecommendationWithBook = {
  recommendation: BookRecommendation;
  book: Book;
};
