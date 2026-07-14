"use client";

import { useMemo, useState } from "react";

import {
  BookDetailPanel,
  BookListCard,
} from "@/components/book-lens-shell";
import { ActiveFilterChips, FilterControls } from "@/components/filter-controls";
import {
  getRecommendationsWithBooks,
  type BookLensData,
} from "@/lib/data";
import {
  filterDisplayTopTags,
  TOP_TAGS_COLLAPSED_COUNT,
  TOP_TAGS_EXPANDED_COUNT,
} from "@/lib/display-tags";
import {
  clearFilterChip,
  defaultBookFilters,
  filterBooks,
  getDecadeOptions,
  type ActiveFilterChip,
  type BookFilters,
} from "@/lib/filters";
import { paginateItems, RESULTS_PAGE_SIZE } from "@/lib/pagination";
import {
  buttonPrimaryClassName,
  contentContainerClassName,
  dataBadgeClassName,
  pageShellClassName,
  warningBannerClassName,
} from "@/lib/ui";

type BookExplorerProps = {
  data: BookLensData;
  loadWarning?: string;
};

const pagerButtonClassName =
  "rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-700 ring-1 ring-slate-200 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-white";

export function BookExplorer({ data, loadWarning }: BookExplorerProps) {
  const { books, topTags, recommendations, source } = data;
  const [filters, setFilters] = useState<BookFilters>(defaultBookFilters);
  const [selectedBookId, setSelectedBookId] = useState(books[0]?.id ?? "");
  const [showAllTopTags, setShowAllTopTags] = useState(false);
  const [tagSearchQuery, setTagSearchQuery] = useState("");
  const [resultsPage, setResultsPage] = useState(1);

  const decadeOptions = useMemo(() => getDecadeOptions(books), [books]);

  const displayTopTags = useMemo(() => filterDisplayTopTags(topTags), [topTags]);

  const tagSearch = tagSearchQuery.trim();
  const tagSearchActive = tagSearch.length > 0;

  const searchedTopTags = useMemo(() => {
    const query = tagSearch.toLowerCase();
    if (!query) {
      return displayTopTags;
    }
    return displayTopTags.filter((item) => item.tag.toLowerCase().includes(query));
  }, [displayTopTags, tagSearch]);

  const visibleTopTags = useMemo(() => {
    if (tagSearchActive) {
      return searchedTopTags.slice(0, TOP_TAGS_EXPANDED_COUNT);
    }
    if (showAllTopTags) {
      return searchedTopTags.slice(0, TOP_TAGS_EXPANDED_COUNT);
    }
    return searchedTopTags.slice(0, TOP_TAGS_COLLAPSED_COUNT);
  }, [searchedTopTags, showAllTopTags, tagSearchActive]);

  const hiddenTopTagCount = tagSearchActive
    ? 0
    : Math.max(
        0,
        searchedTopTags.length -
          (showAllTopTags ? TOP_TAGS_EXPANDED_COUNT : TOP_TAGS_COLLAPSED_COUNT),
      );

  const visibleBooks = useMemo(() => filterBooks(books, filters), [books, filters]);

  const {
    pageItems: pageBooks,
    totalPages,
    page,
    startIndex,
    endIndex,
  } = useMemo(
    () => paginateItems(visibleBooks, resultsPage, RESULTS_PAGE_SIZE),
    [visibleBooks, resultsPage],
  );

  const selectedBook = useMemo(() => {
    if (pageBooks.length === 0) {
      return undefined;
    }
    return pageBooks.find((book) => book.id === selectedBookId) ?? pageBooks[0];
  }, [pageBooks, selectedBookId]);

  const recommendationPairs = selectedBook
    ? getRecommendationsWithBooks(books, recommendations, selectedBook.id)
    : [];

  function updateFilters(next: BookFilters) {
    setFilters(next);
    setResultsPage(1);
  }

  function toggleIncludedTag(tag: string) {
    setFilters((current) => {
      const active = current.includeTags.includes(tag);
      return {
        ...current,
        includeTags: active
          ? current.includeTags.filter((item) => item !== tag)
          : [...current.includeTags, tag],
        excludeTags: current.excludeTags.filter((item) => item !== tag),
      };
    });
    setResultsPage(1);
  }

  function toggleExcludedTag(tag: string) {
    setFilters((current) => {
      const active = current.excludeTags.includes(tag);
      return {
        ...current,
        includeTags: current.includeTags.filter((item) => item !== tag),
        excludeTags: active
          ? current.excludeTags.filter((item) => item !== tag)
          : [...current.excludeTags, tag],
      };
    });
    setResultsPage(1);
  }

  function clearChip(chip: ActiveFilterChip) {
    setFilters((current) => clearFilterChip(current, chip));
    setResultsPage(1);
  }

  function clearAllFilters() {
    setFilters(defaultBookFilters);
    setResultsPage(1);
  }

  const dataSourceLabel = source === "supabase" ? "Supabase" : "Sample fixture";
  const rangeLabel =
    visibleBooks.length === 0
      ? "0 of 0"
      : `${startIndex + 1}–${endIndex} of ${visibleBooks.length}`;

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
              <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
                Explore
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
            onClearAll={clearAllFilters}
          />

          <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Tag filters
                </p>
                <p className="mt-0.5 text-xs text-slate-500">Top catalog tags</p>
              </div>
              <label className="block sm:w-72">
                <span className="sr-only">Search tags</span>
                <input
                  type="search"
                  value={tagSearchQuery}
                  onChange={(event) => setTagSearchQuery(event.target.value)}
                  placeholder="Search tags"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none ring-teal-500 placeholder:text-slate-400 focus:ring-2"
                />
              </label>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {visibleTopTags.map((item) => (
                <span
                  key={item.tag}
                  className={`inline-flex items-center rounded-full text-xs font-medium ring-1 ${
                    filters.excludeTags.includes(item.tag)
                      ? "bg-rose-50 text-rose-800 ring-rose-100"
                      : filters.includeTags.includes(item.tag)
                        ? "bg-teal-700 text-white ring-teal-700"
                        : "bg-white text-slate-700 ring-slate-200"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => toggleIncludedTag(item.tag)}
                    className="rounded-l-full px-3 py-1.5 transition-colors hover:bg-black/5"
                    aria-label={`Include ${item.tag}`}
                    aria-pressed={filters.includeTags.includes(item.tag)}
                  >
                    {item.tag}
                    <span className="ml-1 opacity-70">{item.bookCount}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleExcludedTag(item.tag)}
                    className="rounded-r-full border-l border-current/15 px-2 py-1.5 transition-colors hover:bg-black/5"
                    aria-label={`Exclude ${item.tag}`}
                    aria-pressed={filters.excludeTags.includes(item.tag)}
                    title={`Exclude ${item.tag}`}
                  >
                    -
                  </button>
                </span>
              ))}
              {!tagSearchActive && hiddenTopTagCount > 0 ? (
                <button
                  type="button"
                  onClick={() => setShowAllTopTags((current) => !current)}
                  className="rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200 transition-colors hover:bg-slate-50"
                >
                  {showAllTopTags && !tagSearchQuery.trim()
                    ? "Show fewer"
                    : `Show more (+${hiddenTopTagCount})`}
                </button>
              ) : null}
              {tagSearchActive && visibleTopTags.length === 0 ? (
                <p className="px-1 py-1.5 text-xs text-slate-500">
                  No top tags match {tagSearch}.
                </p>
              ) : null}
            </div>
          </div>
        </div>
      </header>

      <div className={`${contentContainerClassName} grid gap-6 py-6 pb-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-8`}>
        <section aria-label="Book results" className="min-w-0">
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Results</h2>
              <p className="mt-0.5 text-xs text-slate-500">{rangeLabel}</p>
            </div>
            {totalPages > 1 ? (
              <p className="text-xs text-slate-500">
                Page {page} of {totalPages}
              </p>
            ) : null}
          </div>

          {pageBooks.length > 0 ? (
            <>
              <div className="space-y-3">
                {pageBooks.map((book) => (
                  <BookListCard
                    key={book.id}
                    book={book}
                    selected={selectedBook?.id === book.id}
                    onSelect={setSelectedBookId}
                  />
                ))}
              </div>

              {totalPages > 1 ? (
                <nav
                  className="mt-4 flex items-center justify-between gap-3"
                  aria-label="Results pagination"
                >
                  <button
                    type="button"
                    className={pagerButtonClassName}
                    disabled={page <= 1}
                    onClick={() => setResultsPage(page - 1)}
                  >
                    Previous
                  </button>
                  <p className="text-xs font-medium text-slate-600">
                    Page {page} of {totalPages}
                  </p>
                  <button
                    type="button"
                    className={pagerButtonClassName}
                    disabled={page >= totalPages}
                    onClick={() => setResultsPage(page + 1)}
                  >
                    Next
                  </button>
                </nav>
              ) : null}
            </>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
              <p className="text-sm font-medium text-slate-900">No books match these filters.</p>
              <p className="mt-1 text-sm text-slate-600">
                Try removing a filter chip or clearing all filters to restore the full list.
              </p>
              <button
                type="button"
                onClick={clearAllFilters}
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
      </div>
    </div>
  );
}
