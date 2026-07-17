"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { BookCover } from "@/components/book-cover";
import {
  ConfirmBookActionDialog,
} from "@/components/confirm-book-action-dialog";
import { LogBookControls } from "@/components/log-book-controls";
import { useUserProfile } from "@/hooks/use-user-profile";
import type { BookLensData } from "@/lib/data";
import { paginateItems } from "@/lib/pagination";
import type { Book } from "@/lib/types";
import {
  buttonPrimaryClassName,
  contentContainerClassName,
  dataBadgeClassName,
  linkClassName,
  pageShellClassName,
  warningBannerClassName,
} from "@/lib/ui";
import {
  deriveTaste,
  getLogEntry,
  LOG_STATUS_LABELS,
  parseGenresInput,
  updatePreferences,
  upsertLogEntry,
  type LogStatus,
  type PreferredLength,
  type ReadingLogEntry,
  type ReadingPace,
} from "@/lib/user-profile";

type PendingAddConfirm = {
  book: Pick<Book, "id" | "title" | "author">;
};

type ProfilePageProps = {
  data: BookLensData;
  loadWarning?: string;
};

type StatusFilter = "all" | LogStatus;
type RatingFilter = "all" | "rated" | "unrated" | "4plus";
type LogSort = "updated" | "rating" | "title";

const LOG_PAGE_SIZE = 10;

const pagerButtonClassName =
  "rounded-full bg-paper-raised px-3 py-1.5 text-xs font-semibold text-ink-soft ring-1 ring-rule transition-colors hover:bg-paper-deep disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-paper-raised";

export function ProfilePageClient({ data, loadWarning }: ProfilePageProps) {
  const { books, source } = data;
  const { profile, setProfile, hydrated } = useUserProfile();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [ratingFilter, setRatingFilter] = useState<RatingFilter>("all");
  const [logSort, setLogSort] = useState<LogSort>("updated");
  const [logFilterQuery, setLogFilterQuery] = useState("");
  const [catalogQuery, setCatalogQuery] = useState("");
  const [logPage, setLogPage] = useState(1);
  const [genresDraft, setGenresDraft] = useState<string | null>(null);
  const [pendingConfirm, setPendingConfirm] = useState<PendingAddConfirm | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!statusMessage) {
      return;
    }
    const timer = window.setTimeout(() => setStatusMessage(null), 2500);
    return () => window.clearTimeout(timer);
  }, [statusMessage]);

  const bookById = useMemo(() => new Map(books.map((book) => [book.id, book])), [books]);
  const taste = useMemo(() => deriveTaste(profile, books), [profile, books]);
  const genresInput =
    genresDraft ?? profile.preferences.favoriteGenres.join(", ");

  const filteredLog = useMemo(() => {
    const query = logFilterQuery.trim().toLowerCase();

    const filtered = profile.log.filter((entry) => {
      if (statusFilter !== "all" && entry.status !== statusFilter) {
        return false;
      }
      if (ratingFilter === "rated" && entry.rating === null) {
        return false;
      }
      if (ratingFilter === "unrated" && entry.rating !== null) {
        return false;
      }
      if (ratingFilter === "4plus" && (entry.rating === null || entry.rating < 4)) {
        return false;
      }
      if (!query) {
        return true;
      }
      const book = bookById.get(entry.bookId);
      const haystack = [
        book?.title ?? "",
        book?.author ?? "",
        entry.note,
        entry.bookId,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });

    return filtered.sort((left, right) => {
      if (logSort === "rating") {
        const leftRating = left.rating ?? -1;
        const rightRating = right.rating ?? -1;
        if (rightRating !== leftRating) {
          return rightRating - leftRating;
        }
      }
      if (logSort === "title") {
        const leftTitle = bookById.get(left.bookId)?.title ?? left.bookId;
        const rightTitle = bookById.get(right.bookId)?.title ?? right.bookId;
        const compared = leftTitle.localeCompare(rightTitle);
        if (compared !== 0) {
          return compared;
        }
      }
      return right.updatedAt.localeCompare(left.updatedAt);
    });
  }, [profile.log, statusFilter, ratingFilter, logFilterQuery, logSort, bookById]);

  const {
    pageItems: pageLog,
    totalPages,
    page,
    startIndex,
    endIndex,
  } = useMemo(
    () => paginateItems(filteredLog, logPage, LOG_PAGE_SIZE),
    [filteredLog, logPage],
  );

  const searchHits = useMemo(() => {
    const query = catalogQuery.trim().toLowerCase();
    if (query.length < 2) {
      return [] as Book[];
    }
    return books
      .filter(
        (book) =>
          book.title.toLowerCase().includes(query) ||
          book.author.toLowerCase().includes(query),
      )
      .filter((book) => !getLogEntry(profile, book.id))
      .slice(0, 8);
  }, [books, catalogQuery, profile]);

  function resetLogPage() {
    setLogPage(1);
  }

  function handleBookConfirm() {
    if (!pendingConfirm) {
      return;
    }
    const { book } = pendingConfirm;
    setProfile((current) => {
      if (getLogEntry(current, book.id)) {
        return current;
      }
      return upsertLogEntry(current, { bookId: book.id, status: "want" });
    });
    setCatalogQuery("");
    resetLogPage();
    setStatusMessage("Added to profile");
    setPendingConfirm(null);
  }

  function setStatus(next: StatusFilter) {
    setStatusFilter(next);
    resetLogPage();
  }

  function setRating(next: RatingFilter) {
    setRatingFilter(next);
    resetLogPage();
  }

  function setSort(next: LogSort) {
    setLogSort(next);
    resetLogPage();
  }

  function savePreferences(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const preferredLength = String(form.get("preferredLength") || "any") as PreferredLength;
    const pace = String(form.get("pace") || "any") as ReadingPace;
    const minRaw = String(form.get("minCommunityRating") || "").trim();
    const minCommunityRating = minRaw ? Number(minRaw) : null;

    setProfile((current) =>
      updatePreferences(current, {
        favoriteGenres: parseGenresInput(genresInput),
        preferredLength,
        pace,
        minCommunityRating:
          minCommunityRating !== null && Number.isFinite(minCommunityRating)
            ? minCommunityRating
            : null,
      }),
    );
    setGenresDraft(null);
  }

  const dataSourceLabel = source === "supabase" ? "Supabase" : "Sample fixture";
  const rangeLabel =
    filteredLog.length === 0
      ? "0 of 0"
      : `${startIndex + 1}–${endIndex} of ${filteredLog.length}`;

  return (
    <div className={pageShellClassName}>
      {loadWarning ? (
        <div className={warningBannerClassName} role="status">
          {loadWarning}
        </div>
      ) : null}

      <div className={`${contentContainerClassName} max-w-5xl py-8 sm:py-12`}>
        <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-walnut">
              Your private reading record
            </p>
            <h1 className="mt-2 text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
              My Library
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-soft">
              Log books, rate what you finish, and build a local taste profile for compatibility
              scoring. Saved in this browser only.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className={dataBadgeClassName}>Data: {dataSourceLabel}</span>
            <span className={`${dataBadgeClassName} bg-walnut-soft text-walnut-deep ring-walnut/10`}>
              {profile.log.length} logged
            </span>
          </div>
        </header>

        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <section className="reading-room-card rounded-2xl p-5 sm:p-6">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-ink">Reading log</h2>
                <p className="mt-0.5 text-xs text-ink-faint">{rangeLabel}</p>
              </div>
              {totalPages > 1 ? (
                <p className="text-xs text-ink-faint">
                  Page {page} of {totalPages}
                </p>
              ) : null}
            </div>

            <div className="mt-3 flex flex-wrap gap-1.5">
              {(["all", "want", "reading", "read"] as StatusFilter[]).map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setStatus(status)}
                  className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                    statusFilter === status
                      ? "bg-forest text-white"
                      : "bg-paper-deep text-ink-soft ring-1 ring-rule"
                  }`}
                >
                  {status === "all" ? "All" : LOG_STATUS_LABELS[status]}
                </button>
              ))}
            </div>

            <div className="mt-3 flex flex-wrap gap-1.5">
              {(
                [
                  ["all", "Any rating"],
                  ["rated", "Rated"],
                  ["unrated", "Unrated"],
                  ["4plus", "4★+"],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setRating(value)}
                  className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                    ratingFilter === value
                      ? "bg-walnut text-white"
                      : "bg-paper-deep text-ink-soft ring-1 ring-rule"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
              <label className="block min-w-0">
                <span className="sr-only">Filter log</span>
                <input
                  type="search"
                  value={logFilterQuery}
                  onChange={(event) => {
                    setLogFilterQuery(event.target.value);
                    resetLogPage();
                  }}
                  placeholder="Filter log by title, author, or note"
                  className="w-full rounded-xl border border-rule bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-forest focus:ring-2 focus:ring-forest/20"
                />
              </label>
              <label className="block">
                <span className="sr-only">Sort log</span>
                <select
                  value={logSort}
                  onChange={(event) => setSort(event.target.value as LogSort)}
                  className="w-full rounded-xl border border-rule bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-forest focus:ring-2 focus:ring-forest/20 sm:w-40"
                >
                  <option value="updated">Newest</option>
                  <option value="rating">Highest rated</option>
                  <option value="title">Title A–Z</option>
                </select>
              </label>
            </div>

            <label className="mt-4 block">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-walnut">Add from catalog</span>
              <input
                type="search"
                value={catalogQuery}
                onChange={(event) => setCatalogQuery(event.target.value)}
                placeholder="Search title or author to log"
                className="mt-1.5 w-full rounded-xl border border-rule bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-forest focus:ring-2 focus:ring-forest/20"
              />
            </label>

            {searchHits.length > 0 ? (
              <ul className="mt-2 space-y-2">
                {searchHits.map((book) => (
                  <li
                    key={book.id}
                    className="flex items-center justify-between gap-3 rounded-lg bg-paper-deep/55 px-3 py-2 ring-1 ring-rule"
                  >
                    <BookCover book={book} size="sm" />
                    <div className="min-w-0 flex-1">
                      <Link
                        href={`/books/${book.id}`}
                        className={`block truncate text-sm font-medium ${linkClassName}`}
                      >
                        {book.title}
                      </Link>
                      <p className="truncate text-xs text-ink-faint">{book.author}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setPendingConfirm({
                          book: {
                            id: book.id,
                            title: book.title,
                            author: book.author,
                          },
                        })
                      }
                      className="shrink-0 rounded-full bg-forest px-3 py-1 text-xs font-semibold text-white hover:bg-forest-deep"
                    >
                      Log
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}

            <div className="mt-5 space-y-3">
              {!hydrated ? (
                <p className="text-sm text-ink-faint">Loading saved profile…</p>
              ) : filteredLog.length === 0 ? (
                <p className="rounded-lg border border-dashed border-rule px-4 py-8 text-center text-sm text-ink-faint">
                  No books in this view yet. Adjust filters, search above, or log from{" "}
                  <Link href="/explore" className={linkClassName}>
                    Discover
                  </Link>
                  .
                </p>
              ) : (
                <>
                  {pageLog.map((entry: ReadingLogEntry) => {
                    const book = bookById.get(entry.bookId);
                    return (
                      <article
                        key={entry.bookId}
                        className="rounded-xl border border-rule bg-paper-deep/35 p-4"
                      >
                        <div className="flex gap-3">
                          {book ? <BookCover book={book} size="sm" /> : null}
                          <div className="min-w-0 flex-1">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                            {book ? (
                              <Link
                                href={`/books/${entry.bookId}`}
                                className={`block truncate text-sm font-semibold ${linkClassName}`}
                              >
                                {book.title}
                              </Link>
                            ) : (
                              <h3 className="truncate text-sm font-semibold text-ink">
                                Unknown book
                              </h3>
                            )}
                            <p className="text-xs text-ink-soft">
                              {book?.author ?? entry.bookId}
                            </p>
                              </div>
                            </div>
                            <LogBookControls
                              book={{
                                id: entry.bookId,
                                title: book?.title ?? "Unknown book",
                                author: book?.author ?? entry.bookId,
                              }}
                              compact
                            />
                            <label className="mt-2 block">
                              <span className="sr-only">Note</span>
                              <input
                                type="text"
                                value={entry.note}
                                onChange={(event) =>
                                  setProfile((current) =>
                                    upsertLogEntry(current, {
                                      bookId: entry.bookId,
                                      note: event.target.value,
                                    }),
                                  )
                                }
                                placeholder="Optional note"
                                className="w-full rounded-lg border border-rule bg-paper-raised px-3 py-1.5 text-xs text-ink outline-none focus:border-forest focus:ring-2 focus:ring-forest/20"
                              />
                            </label>
                          </div>
                        </div>
                      </article>
                    );
                  })}

                  {totalPages > 1 ? (
                    <nav
                      className="flex items-center justify-between gap-3 pt-1"
                      aria-label="Reading log pagination"
                    >
                      <button
                        type="button"
                        className={pagerButtonClassName}
                        disabled={page <= 1}
                        onClick={() => setLogPage(page - 1)}
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
                        onClick={() => setLogPage(page + 1)}
                      >
                        Next
                      </button>
                    </nav>
                  ) : null}
                </>
              )}
            </div>
          </section>

          <div className="space-y-6">
            <section className="reading-room-card rounded-2xl p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-walnut">From your shelves</p>
              <h2 className="mt-1 text-2xl font-semibold text-ink">Taste profile</h2>
              <p className="mt-1 text-xs text-ink-faint">
                Derived from your log{taste.ratedCount ? ` · avg ${taste.averagePersonalRating}★` : ""}
              </p>

              {taste.logCount === 0 ? (
                <p className="mt-4 text-sm text-ink-faint">
                  Log and rate books to see theme and tag signals here.
                </p>
              ) : (
                <>
                  <div className="mt-4">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-walnut">
                      Top tags
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {taste.topTags.length > 0 ? (
                        taste.topTags.map((item) => (
                          <span
                            key={item.tag}
                            className="rounded-full bg-forest-soft px-2.5 py-0.5 text-xs font-medium text-forest"
                          >
                            {item.tag}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-ink-faint">No displayable tags yet</span>
                      )}
                    </div>
                  </div>
                  <div className="mt-4">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-walnut">
                      Theme lean
                    </p>
                    <ul className="mt-2 space-y-1.5">
                      {taste.themeScores
                        .filter((item) => item.score > 0)
                        .slice(0, 5)
                        .map((item) => (
                          <li
                            key={item.id}
                            className="grid grid-cols-[minmax(0,1fr)_2.5rem] items-center gap-2 text-xs"
                          >
                            <span className="truncate text-ink-soft">{item.label}</span>
                            <span className="text-right font-medium tabular-nums text-ink-faint">
                              {item.score}%
                            </span>
                          </li>
                        ))}
                    </ul>
                  </div>
                  <p className="mt-4 text-xs text-ink-faint">
                    Usual length:{" "}
                    <span className="font-medium text-ink">{taste.preferredLength}</span>
                  </p>
                </>
              )}

              <Link href="/compatibility" className={`mt-4 inline-block ${linkClassName}`}>
                Open matches →
              </Link>
            </section>

            <section
              id="preferences"
              className="reading-room-card rounded-2xl p-5"
            >
              <h2 className="text-2xl font-semibold text-ink">Preferences</h2>
              <p className="mt-1 text-xs text-ink-faint">Manual overrides for matching</p>

              <form className="mt-4 space-y-3" onSubmit={savePreferences}>
                <label className="block">
                  <span className="text-xs font-medium text-ink-soft">Favorite genres</span>
                  <input
                    value={genresInput}
                    onChange={(event) => setGenresDraft(event.target.value)}
                    placeholder="science fiction, mystery"
                    className="mt-1 w-full rounded-lg border border-rule bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-forest focus:ring-2 focus:ring-forest/20"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-ink-soft">Preferred length</span>
                  <select
                    name="preferredLength"
                    defaultValue={profile.preferences.preferredLength}
                    className="mt-1 w-full rounded-lg border border-rule bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-forest focus:ring-2 focus:ring-forest/20"
                  >
                    <option value="any">Any</option>
                    <option value="short">Short</option>
                    <option value="medium">Medium</option>
                    <option value="long">Long</option>
                  </select>
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-ink-soft">Minimum community rating</span>
                  <input
                    name="minCommunityRating"
                    type="number"
                    min={0}
                    max={5}
                    step={0.1}
                    defaultValue={profile.preferences.minCommunityRating ?? ""}
                    placeholder="e.g. 3.5"
                    className="mt-1 w-full rounded-lg border border-rule bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-forest focus:ring-2 focus:ring-forest/20"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-ink-soft">Reading pace</span>
                  <select
                    name="pace"
                    defaultValue={profile.preferences.pace}
                    className="mt-1 w-full rounded-lg border border-rule bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-forest focus:ring-2 focus:ring-forest/20"
                  >
                    <option value="any">Any</option>
                    <option value="fast">Fast</option>
                    <option value="moderate">Moderate</option>
                    <option value="slow">Slow</option>
                  </select>
                </label>
                <button type="submit" className={buttonPrimaryClassName}>
                  Save preferences
                </button>
              </form>
            </section>
          </div>
        </div>
      </div>

      {statusMessage ? (
        <div
          className="pointer-events-none fixed bottom-4 left-1/2 z-40 -translate-x-1/2 rounded-full bg-forest px-3 py-1.5 text-xs font-medium text-white shadow-sm"
          role="status"
        >
          {statusMessage}
        </div>
      ) : null}

      {pendingConfirm ? (
        <ConfirmBookActionDialog
          key={`add-${pendingConfirm.book.id}`}
          book={pendingConfirm.book}
          action="add"
          open
          onConfirm={handleBookConfirm}
          onCancel={() => setPendingConfirm(null)}
        />
      ) : null}
    </div>
  );
}
