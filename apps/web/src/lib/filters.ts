import type { Book } from "./types";

export type BookFilters = {
  searchQuery: string;
  includeTags: string[];
  excludeTags: string[];
  decade: string | null;
  minPageCount: number | null;
  maxPageCount: number | null;
  minAverageRating: number | null;
  minRatingCount: number | null;
};

export type ActiveFilterChip = {
  key: keyof BookFilters;
  label: string;
  value?: string;
};

export const defaultBookFilters: BookFilters = {
  searchQuery: "",
  includeTags: [],
  excludeTags: [],
  decade: null,
  minPageCount: null,
  maxPageCount: null,
  minAverageRating: null,
  minRatingCount: null,
};

export function getDecadeOptions(books: Book[]): string[] {
  const decades = new Set<string>();
  for (const book of books) {
    if (book.decade) {
      decades.add(book.decade);
    }
  }
  return Array.from(decades).sort();
}

export function bookMatchesFilters(book: Book, filters: BookFilters): boolean {
  const query = filters.searchQuery.trim().toLowerCase();
  if (query.length > 0) {
    const matchesSearch =
      book.title.toLowerCase().includes(query) ||
      book.author.toLowerCase().includes(query) ||
      book.description.toLowerCase().includes(query) ||
      book.tags.some((tag) => tag.toLowerCase().includes(query));
    if (!matchesSearch) {
      return false;
    }
  }

  const bookTags = new Set(book.tags.map((tag) => tag.toLowerCase()));

  if (filters.includeTags.length > 0) {
    const includesEveryTag = filters.includeTags.every((tag) => bookTags.has(tag));
    if (!includesEveryTag) {
      return false;
    }
  }

  if (filters.excludeTags.length > 0) {
    const hasExcludedTag = filters.excludeTags.some((tag) => bookTags.has(tag));
    if (hasExcludedTag) {
      return false;
    }
  }

  if (filters.decade !== null) {
    if (book.decade !== filters.decade) {
      return false;
    }
  }

  if (filters.minPageCount !== null) {
    if (book.pageCount === null || book.pageCount < filters.minPageCount) {
      return false;
    }
  }

  if (filters.maxPageCount !== null) {
    if (book.pageCount === null || book.pageCount > filters.maxPageCount) {
      return false;
    }
  }

  if (filters.minAverageRating !== null) {
    if (book.averageRating === null || book.averageRating < filters.minAverageRating) {
      return false;
    }
  }

  if (filters.minRatingCount !== null) {
    if (book.ratingCount === null || book.ratingCount < filters.minRatingCount) {
      return false;
    }
  }

  return true;
}

export function filterBooks(books: Book[], filters: BookFilters): Book[] {
  return books.filter((book) => bookMatchesFilters(book, filters));
}

export function getActiveFilterChips(filters: BookFilters): ActiveFilterChip[] {
  const chips: ActiveFilterChip[] = [];

  const search = filters.searchQuery.trim();
  if (search) {
    chips.push({ key: "searchQuery", label: `Search: ${search}` });
  }

  for (const tag of filters.includeTags) {
    chips.push({ key: "includeTags", label: `Includes: ${tag}`, value: tag });
  }

  for (const tag of filters.excludeTags) {
    chips.push({ key: "excludeTags", label: `Excludes: ${tag}`, value: tag });
  }

  if (filters.decade) {
    chips.push({ key: "decade", label: `Decade: ${filters.decade}` });
  }

  if (filters.minPageCount !== null || filters.maxPageCount !== null) {
    const minLabel =
      filters.minPageCount !== null ? filters.minPageCount.toLocaleString() : "any";
    const maxLabel =
      filters.maxPageCount !== null ? filters.maxPageCount.toLocaleString() : "any";
    chips.push({
      key: "minPageCount",
      label: `Pages: ${minLabel}–${maxLabel}`,
    });
  }

  if (filters.minAverageRating !== null) {
    chips.push({
      key: "minAverageRating",
      label: `Rating ≥ ${filters.minAverageRating.toFixed(1)}`,
    });
  }

  if (filters.minRatingCount !== null) {
    chips.push({
      key: "minRatingCount",
      label: `Ratings ≥ ${filters.minRatingCount.toLocaleString()}`,
    });
  }

  return chips;
}

export function clearFilterChip(filters: BookFilters, chip: ActiveFilterChip): BookFilters {
  const { key, value } = chip;

  switch (key) {
    case "searchQuery":
      return { ...filters, searchQuery: "" };
    case "includeTags":
      return {
        ...filters,
        includeTags: value
          ? filters.includeTags.filter((tag) => tag !== value)
          : [],
      };
    case "excludeTags":
      return {
        ...filters,
        excludeTags: value
          ? filters.excludeTags.filter((tag) => tag !== value)
          : [],
      };
    case "decade":
      return { ...filters, decade: null };
    case "minPageCount":
      return { ...filters, minPageCount: null, maxPageCount: null };
    case "minAverageRating":
      return { ...filters, minAverageRating: null };
    case "minRatingCount":
      return { ...filters, minRatingCount: null };
    default:
      return filters;
  }
}

export function hasActiveFilters(filters: BookFilters): boolean {
  return getActiveFilterChips(filters).length > 0;
}
