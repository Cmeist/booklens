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
  "rounded-full bg-paper-raised px-3 py-1.5 text-xs font-semibold text-ink-soft ring-1 ring-rule transition-colors hover:bg-paper-deep disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-paper-raised";

export function BookExplorer({ data, loadWarning }: BookExplorerProps) {
  const { books, topTags, recommendations, source } = data;
  const [filters, setFilters] = useState<BookFilters>(defaultBookFilters);
  const [selectedBookId, setSelectedBookId] = useState(books[0]?.id ?? "");
  const [showAllTopTags, setShowAllTopTags] = useState(false);
  const [tagSearchQuery, setTagSearchQuery] = useState("");
  const [resultsPage, setResultsPage] = useState(1);
  const [filtersOpen, setFiltersOpen] = useState(false);

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

      <header className="border-b border-rule bg-paper-raised/75">
        <div className={`${contentContainerClassName} flex flex-col gap-5 py-7 sm:py-9`}>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-walnut">Browse the shelves</p>
              <h1 className="mt-1 text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
                Discover
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-soft">
                Search the collection, refine by the details that matter, and open any
                volume to see its themes and explainable recommendations.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <div className={`${dataBadgeClassName} bg-walnut-soft text-walnut-deep ring-walnut/10`}>
                {visibleBooks.length} of {books.length} books shown
              </div>
              <div className={dataBadgeClassName}>Data: {dataSourceLabel}</div>
            </div>
          </div>

          <button
            type="button"
            className="flex w-full items-center justify-between rounded-xl border border-rule bg-paper px-4 py-3 text-sm font-semibold text-ink lg:hidden"
            aria-expanded={filtersOpen}
            aria-controls="discover-filter-panel"
            onClick={() => setFiltersOpen((current) => !current)}
          >
            Refine this shelf
            <span className="text-walnut" aria-hidden="true">
              {filtersOpen ? "Hide" : "Show"}
            </span>
          </button>

          <div
            id="discover-filter-panel"
            className={`${filtersOpen ? "space-y-4" : "hidden"} lg:block lg:space-y-4`}
          >
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

            <div className="reading-room-card rounded-2xl p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-walnut">
                  Tag filters
                </p>
                <p className="mt-0.5 text-xs text-ink-faint">Include a shelf or explicitly exclude one</p>
              </div>
              <label className="block sm:w-72">
                <span className="sr-only">Search tags</span>
                <input
                  type="search"
                  value={tagSearchQuery}
                  onChange={(event) => setTagSearchQuery(event.target.value)}
                  placeholder="Search tags"
                  className="w-full rounded-xl border border-rule bg-paper px-3 py-2 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-forest focus:ring-2 focus:ring-forest/20"
                />
              </label>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {visibleTopTags.map((item) => (
                <span
                  key={item.tag}
                  className={`inline-flex items-center rounded-full text-xs font-medium ring-1 ${
                    filters.excludeTags.includes(item.tag)
                      ? "bg-danger-soft text-danger ring-danger/20"
                      : filters.includeTags.includes(item.tag)
                        ? "bg-forest text-white ring-forest"
                        : "bg-paper-raised text-ink-soft ring-rule"
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
                    Not
                  </button>
                </span>
              ))}
              {!tagSearchActive && hiddenTopTagCount > 0 ? (
                <button
                  type="button"
                  onClick={() => setShowAllTopTags((current) => !current)}
                  className="rounded-full bg-paper-raised px-3 py-1.5 text-xs font-medium text-ink-soft ring-1 ring-rule transition-colors hover:bg-paper-deep"
                >
                  {showAllTopTags && !tagSearchQuery.trim()
                    ? "Show fewer"
                    : `Show more (+${hiddenTopTagCount})`}
                </button>
              ) : null}
              {tagSearchActive && visibleTopTags.length === 0 ? (
                <p className="px-1 py-1.5 text-xs text-ink-faint">
                  No top tags match {tagSearch}.
                </p>
              ) : null}
            </div>
            </div>
          </div>
        </div>
      </header>

      <div className={`${contentContainerClassName} grid gap-6 py-6 pb-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-8`}>
        <section aria-label="Book results" className="min-w-0">
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-walnut">Current selection</p>
              <h2 className="mt-0.5 text-2xl font-semibold text-ink">Results</h2>
              <p className="mt-0.5 text-xs text-ink-faint">{rangeLabel}</p>
            </div>
            {totalPages > 1 ? (
              <p className="text-xs text-ink-faint">
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
                  <p className="text-xs font-medium text-ink-soft">
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
            <div className="rounded-2xl border border-dashed border-rule-strong bg-paper-raised px-6 py-10 text-center">
              <p className="text-lg font-semibold text-ink">No books match these filters.</p>
              <p className="mt-1 text-sm text-ink-soft">
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
          <div className="order-first min-w-0 lg:order-none lg:self-start">
            <BookDetailPanel book={selectedBook} recommendationPairs={recommendationPairs} />
          </div>
        ) : (
          <div className="hidden rounded-2xl border border-dashed border-rule bg-paper-raised/70 px-5 py-8 text-center text-sm text-ink-faint lg:block">
            Select a book to preview details and similar titles.
          </div>
        )}
      </div>
    </div>
  );
}
