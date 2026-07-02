"use client";

import { useMemo, useState } from "react";

import {
  AnalyticsPreview,
  BookDetailPanel,
  BookListCard,
} from "@/components/book-lens-shell";
import { ActiveFilterChips, FilterControls } from "@/components/filter-controls";
import {
  books,
  getRecommendationsWithBooks,
  topTags,
} from "@/lib/data";
import {
  clearFilterChip,
  defaultBookFilters,
  filterBooks,
  getDecadeOptions,
  type BookFilters,
} from "@/lib/filters";

export function BookExplorer() {
  const [filters, setFilters] = useState<BookFilters>(defaultBookFilters);
  const [selectedBookId, setSelectedBookId] = useState(books[0]?.id ?? "");

  const decadeOptions = useMemo(() => getDecadeOptions(books), []);

  const visibleBooks = useMemo(() => filterBooks(books, filters), [filters]);

  const selectedBook = useMemo(() => {
    if (visibleBooks.length === 0) {
      return undefined;
    }
    return visibleBooks.find((book) => book.id === selectedBookId) ?? visibleBooks[0];
  }, [visibleBooks, selectedBookId]);

  const recommendationPairs = selectedBook
    ? getRecommendationsWithBooks(selectedBook.id)
    : [];

  function updateFilters(next: BookFilters) {
    setFilters(next);
  }

  function setTagFilter(tag: string | null) {
    setFilters((current) => ({ ...current, tag }));
  }

  function clearChip(key: Parameters<typeof clearFilterChip>[1]) {
    setFilters((current) => clearFilterChip(current, key));
  }

  return (
    <div className="min-h-full bg-[#f4f1ea] text-slate-900">
      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
                BookLens
              </p>
              <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
                Book explorer
              </h1>
              <p className="mt-1 max-w-2xl text-sm text-slate-600">
                Search, filter, and inspect explainable recommendations from the sample dataset.
              </p>
            </div>
            <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
              {visibleBooks.length} of {books.length} books shown
            </div>
          </div>

          <FilterControls
            filters={filters}
            decadeOptions={decadeOptions}
            onChange={updateFilters}
          />

          <ActiveFilterChips
            filters={filters}
            onClearChip={clearChip}
            onClearAll={() => setFilters(defaultBookFilters)}
          />

          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Top tags
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setTagFilter(null)}
                className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                  filters.tag === null
                    ? "bg-slate-900 text-white"
                    : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
                }`}
              >
                All tags
              </button>
              {topTags.map((item) => (
                <button
                  key={item.tag}
                  type="button"
                  onClick={() =>
                    setTagFilter(filters.tag === item.tag ? null : item.tag)
                  }
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                    filters.tag === item.tag
                      ? "bg-teal-700 text-white"
                      : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
                  }`}
                >
                  {item.tag}
                  <span className="ml-1 opacity-70">{item.bookCount}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:px-8">
        <section aria-label="Book results">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Results</h2>
          </div>

          {visibleBooks.length > 0 ? (
            <div className="space-y-3">
              {visibleBooks.map((book) => (
                <BookListCard
                  key={book.id}
                  book={book}
                  selected={selectedBook?.id === book.id}
                  onSelect={setSelectedBookId}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
              <p className="text-sm font-medium text-slate-900">No books match these filters.</p>
              <p className="mt-1 text-sm text-slate-600">
                Try removing a filter chip or clearing all filters to restore the full list.
              </p>
              <button
                type="button"
                onClick={() => setFilters(defaultBookFilters)}
                className="mt-4 rounded-full bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800"
              >
                Clear all filters
              </button>
            </div>
          )}
        </section>

        {selectedBook ? (
          <BookDetailPanel book={selectedBook} recommendationPairs={recommendationPairs} />
        ) : null}
      </main>

      <div className="mx-auto max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
        <AnalyticsPreview books={books} topTags={topTags} />
      </div>
    </div>
  );
}
