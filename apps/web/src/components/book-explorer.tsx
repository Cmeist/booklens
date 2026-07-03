"use client";

import { useMemo, useState } from "react";

import {
  BookDetailPanel,
  BookListCard,
} from "@/components/book-lens-shell";
import { AnalyticsSection } from "@/components/analytics-section";
import { ActiveFilterChips, FilterControls } from "@/components/filter-controls";
import {
  buttonPrimaryClassName,
  contentContainerClassName,
  dataBadgeClassName,
  pageShellClassName,
  warningBannerClassName,
} from "@/lib/ui";
import {
  getRecommendationsWithBooks,
  type BookLensData,
} from "@/lib/data";
import {
  clearFilterChip,
  defaultBookFilters,
  filterBooks,
  getDecadeOptions,
  type BookFilters,
} from "@/lib/filters";

type BookExplorerProps = {
  data: BookLensData;
  loadWarning?: string;
};

export function BookExplorer({ data, loadWarning }: BookExplorerProps) {
  const { books, topTags, recommendations, source } = data;
  const [filters, setFilters] = useState<BookFilters>(defaultBookFilters);
  const [selectedBookId, setSelectedBookId] = useState(books[0]?.id ?? "");

  const decadeOptions = useMemo(() => getDecadeOptions(books), [books]);

  const visibleBooks = useMemo(() => filterBooks(books, filters), [books, filters]);

  const selectedBook = useMemo(() => {
    if (visibleBooks.length === 0) {
      return undefined;
    }
    return visibleBooks.find((book) => book.id === selectedBookId) ?? visibleBooks[0];
  }, [visibleBooks, selectedBookId]);

  const recommendationPairs = selectedBook
    ? getRecommendationsWithBooks(books, recommendations, selectedBook.id)
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

  const dataSourceLabel = source === "supabase" ? "Supabase" : "Sample fixture";

  return (
    <div className={pageShellClassName}>
      {loadWarning ? (
        <div className={warningBannerClassName} role="status">
          {loadWarning}
        </div>
      ) : null}

      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className={`${contentContainerClassName} flex flex-col gap-4 py-5`}>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
                BookLens
              </p>
              <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
                Book explorer
              </h1>
              <p className="mt-1 max-w-2xl text-sm text-slate-600">
                Search, filter, and inspect explainable recommendations from the{" "}
                {dataSourceLabel.toLowerCase()} dataset.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <div className={`${dataBadgeClassName} bg-slate-100 text-slate-600 ring-0`}>
                {visibleBooks.length} of {books.length} books shown
              </div>
              <div className={dataBadgeClassName}>Data: {dataSourceLabel}</div>
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

      <main className={`${contentContainerClassName} grid gap-6 py-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-8`}>
        <section aria-label="Book results" className="min-w-0">
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
                className={`mt-4 ${buttonPrimaryClassName}`}
              >
                Clear all filters
              </button>
            </div>
          )}
        </section>

        {selectedBook ? (
          <div className="min-w-0 lg:sticky lg:top-6 lg:self-start">
            <BookDetailPanel book={selectedBook} recommendationPairs={recommendationPairs} />
          </div>
        ) : (
          <div className="hidden rounded-2xl border border-dashed border-slate-200 bg-white/70 px-5 py-8 text-center text-sm text-slate-500 lg:block">
            Select a book to preview details and similar titles.
          </div>
        )}
      </main>

      <div className={`${contentContainerClassName} pb-10`}>
        <AnalyticsSection books={books} topTags={topTags} source={source} />
      </div>
    </div>
  );
}
