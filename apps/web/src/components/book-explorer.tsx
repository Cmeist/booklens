"use client";

import { useMemo, useState } from "react";

import {
  AnalyticsPreview,
  BookDetailPanel,
  BookListCard,
} from "@/components/book-lens-shell";
import {
  books,
  getBookById,
  getRecommendationsWithBooks,
  topTags,
} from "@/lib/data";

export function BookExplorer() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedBookId, setSelectedBookId] = useState(books[0]?.id ?? "");
  const [activeTag, setActiveTag] = useState<string | null>(null);

  const visibleBooks = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return books.filter((book) => {
      const matchesSearch =
        query.length === 0 ||
        book.title.toLowerCase().includes(query) ||
        book.author.toLowerCase().includes(query) ||
        book.description.toLowerCase().includes(query) ||
        book.tags.some((tag) => tag.toLowerCase().includes(query));

      const matchesTag =
        activeTag === null || book.tags.some((tag) => tag.toLowerCase() === activeTag);

      return matchesSearch && matchesTag;
    });
  }, [activeTag, searchQuery]);

  const selectedBook =
    getBookById(selectedBookId) ?? getBookById(visibleBooks[0]?.id ?? "") ?? books[0];

  const recommendationPairs = selectedBook
    ? getRecommendationsWithBooks(selectedBook.id)
    : [];

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
                Search, inspect metadata, and review explainable recommendations from the sample
                dataset.
              </p>
            </div>
            <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
              {visibleBooks.length} of {books.length} books shown
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-[1.4fr_repeat(3,minmax(0,1fr))]">
            <label className="block">
              <span className="sr-only">Search books</span>
              <input
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search title, author, description, or tags"
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm outline-none ring-teal-500 placeholder:text-slate-400 focus:ring-2"
              />
            </label>
            <select
              disabled
              aria-label="Decade filter placeholder"
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-500"
              defaultValue=""
            >
              <option value="">Decade (Phase 4)</option>
            </select>
            <select
              disabled
              aria-label="Minimum rating filter placeholder"
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-500"
              defaultValue=""
            >
              <option value="">Min rating (Phase 4)</option>
            </select>
            <select
              disabled
              aria-label="Page count filter placeholder"
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-500"
              defaultValue=""
            >
              <option value="">Page count (Phase 4)</option>
            </select>
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Top tags
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setActiveTag(null)}
                className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                  activeTag === null
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
                    setActiveTag((current) => (current === item.tag ? null : item.tag))
                  }
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                    activeTag === item.tag
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
            {activeTag ? (
              <button
                type="button"
                onClick={() => setActiveTag(null)}
                className="text-xs font-medium text-teal-700 hover:text-teal-800"
              >
                Clear tag: {activeTag}
              </button>
            ) : null}
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
              <p className="text-sm font-medium text-slate-900">No books match this view.</p>
              <p className="mt-1 text-sm text-slate-600">
                Try clearing the search or tag filter.
              </p>
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
