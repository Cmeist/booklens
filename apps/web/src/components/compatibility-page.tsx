"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { LogBookControls } from "@/components/log-book-controls";
import { useUserProfile } from "@/hooks/use-user-profile";
import {
  scoreCompatibilityWithTaste,
  type CompatibilityDimension,
  type CompatibilityResult,
} from "@/lib/compatibility";
import {
  formatCompatibilityPercent,
  isPartialCompatibility,
  profileHasCompatibilitySignal,
  rankCompatibilityMatches,
  type CompatibilityRankSort,
  type RankedCompatibilityItem,
} from "@/lib/compatibility-rankings";
import type { BookLensData } from "@/lib/data";
import type { Book } from "@/lib/types";
import { deriveTaste } from "@/lib/user-profile";
import {
  contentContainerClassName,
  dataBadgeClassName,
  linkClassName,
  pageShellClassName,
  warningBannerClassName,
} from "@/lib/ui";

type CompatibilityPageProps = {
  data: BookLensData;
  loadWarning?: string;
};

const RANK_LIMIT = 25;

const EMPTY_DIMENSIONS: CompatibilityDimension[] = [
  { id: "overall", label: "Overall fit", score: null },
  { id: "theme", label: "Theme overlap", score: null },
  { id: "tags", label: "Tag overlap", score: null },
  { id: "length", label: "Pace & length", score: null },
  { id: "rating", label: "Rating alignment", score: null },
];

export function CompatibilityPageClient({ data, loadWarning }: CompatibilityPageProps) {
  const searchParams = useSearchParams();
  const requestedBookId = searchParams.get("book") ?? "";
  const { books, source } = data;
  const { profile, hydrated } = useUserProfile();

  const requestedBookExists = Boolean(
    requestedBookId && books.some((book) => book.id === requestedBookId),
  );
  const invalidBookRequest = Boolean(requestedBookId) && !requestedBookExists;

  const [selectedBookId, setSelectedBookId] = useState(
    requestedBookExists ? requestedBookId : "",
  );
  const [query, setQuery] = useState("");
  const [hideRead, setHideRead] = useState(true);
  const [sort, setSort] = useState<CompatibilityRankSort>("match");

  const taste = useMemo(() => deriveTaste(profile, books), [profile, books]);
  const hasSignal = useMemo(
    () => profileHasCompatibilitySignal(profile, books, taste),
    [profile, books, taste],
  );

  const rankings = useMemo(() => {
    if (!hydrated || !hasSignal) {
      return [] as RankedCompatibilityItem[];
    }
    return rankCompatibilityMatches(profile, books, {
      hideRead,
      query,
      sort,
      limit: RANK_LIMIT,
      derivedTaste: taste,
    });
  }, [hydrated, hasSignal, profile, books, hideRead, query, sort, taste]);

  const selectedBook = useMemo(
    () => books.find((book) => book.id === selectedBookId),
    [books, selectedBookId],
  );

  const selectedResult = useMemo((): CompatibilityResult | null => {
    if (!selectedBook || !hydrated || !hasSignal) {
      return null;
    }
    const fromRankings = rankings.find((item) => item.book.id === selectedBook.id);
    if (fromRankings) {
      return fromRankings.result;
    }
    return scoreCompatibilityWithTaste(profile, selectedBook, taste);
  }, [selectedBook, hydrated, hasSignal, rankings, profile, taste]);

  const dataSourceLabel = source === "supabase" ? "Supabase" : "Sample fixture";
  const showPartialNote =
    hasSignal &&
    rankings.some((item) => isPartialCompatibility(item.result));

  return (
    <div className={pageShellClassName}>
      {loadWarning ? (
        <div className={warningBannerClassName} role="status">
          {loadWarning}
        </div>
      ) : null}

      <div className={`${contentContainerClassName} max-w-6xl py-8`}>
        <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
              BookLens
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
              What should I read next?
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Ranked matches from your local profile — themes, tags, length, and rating floor.
            </p>
          </div>
          <span className={dataBadgeClassName}>Data: {dataSourceLabel}</span>
        </header>

        {invalidBookRequest ? (
          <div
            className="mt-6 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm"
            role="status"
          >
            That book link isn&apos;t in this catalog. Browse matches below or{" "}
            <Link href="/explore" className={linkClassName}>
              explore the library
            </Link>
            .
          </div>
        ) : null}

        {!hydrated ? (
          <p className="mt-8 text-sm text-slate-500">Loading your local profile…</p>
        ) : !hasSignal ? (
          <LowSignalChecklist tasteLogCount={taste.logCount} />
        ) : (
          <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1.45fr)_minmax(0,0.85fr)]">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">Top matches for you</h2>
                  <p className="mt-0.5 text-xs text-slate-500">
                    Showing {rankings.length} of up to {RANK_LIMIT}
                    {hideRead ? " · hiding read books" : ""}
                  </p>
                </div>
              </div>

              {showPartialNote ? (
                <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900 ring-1 ring-amber-100">
                  Partial signal — some dimensions are blank until you log more rated books or
                  set preferences.
                </p>
              ) : null}

              <div className="mt-4 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto_auto]">
                <label className="block min-w-0">
                  <span className="sr-only">Search ranked matches</span>
                  <input
                    type="search"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search matches by title or author"
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none ring-teal-500 focus:ring-2"
                  />
                </label>
                <label className="block">
                  <span className="sr-only">Sort matches</span>
                  <select
                    value={sort}
                    onChange={(event) =>
                      setSort(event.target.value as CompatibilityRankSort)
                    }
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none ring-teal-500 focus:ring-2 sm:w-40"
                  >
                    <option value="match">Best match</option>
                    <option value="title">Title A–Z</option>
                    <option value="recent">Recently logged</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700">
                  <input
                    type="checkbox"
                    checked={hideRead}
                    onChange={(event) => setHideRead(event.target.checked)}
                    className="rounded border-slate-300 text-teal-700 focus:ring-teal-500"
                  />
                  Hide read
                </label>
              </div>

              {rankings.length === 0 ? (
                <p className="mt-5 rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500">
                  No matches in this view. Clear search, show read books, or{" "}
                  <Link href="/explore" className={linkClassName}>
                    explore
                  </Link>
                  .
                </p>
              ) : (
                <ul className="mt-5 space-y-3">
                  {rankings.map((item) => (
                    <li key={item.book.id}>
                      <RankedMatchCard
                        item={item}
                        selected={selectedBookId === item.book.id}
                        onSelect={() => setSelectedBookId(item.book.id)}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <aside className="space-y-6">
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-900">Your profile signal</h2>
                <p className="mt-1 text-xs text-slate-500">
                  {taste.logCount} logged · {taste.ratedCount} rated
                </p>
                <ul className="mt-4 space-y-2 text-sm text-slate-700">
                  <li className="rounded-lg bg-slate-50 px-3 py-2 ring-1 ring-slate-100">
                    Favorite genres:{" "}
                    {profile.preferences.favoriteGenres.length > 0
                      ? profile.preferences.favoriteGenres.join(", ")
                      : "—"}
                  </li>
                  <li className="rounded-lg bg-slate-50 px-3 py-2 ring-1 ring-slate-100">
                    Preferred length: {taste.preferredLength}
                  </li>
                  <li className="rounded-lg bg-slate-50 px-3 py-2 ring-1 ring-slate-100">
                    Rating floor: {profile.preferences.minCommunityRating ?? "—"}
                  </li>
                  <li className="rounded-lg bg-slate-50 px-3 py-2 ring-1 ring-slate-100">
                    Top taste tags:{" "}
                    {taste.topTags.length > 0
                      ? taste.topTags
                          .slice(0, 4)
                          .map((item) => item.tag)
                          .join(", ")
                      : "—"}
                  </li>
                </ul>
                <Link href="/profile" className={`mt-4 inline-block ${linkClassName}`}>
                  Edit profile →
                </Link>
              </section>

              <SelectedBookPanel
                selectedBook={selectedBook}
                result={selectedResult}
              />
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}

function LowSignalChecklist({ tasteLogCount }: { tasteLogCount: number }) {
  return (
    <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">Build a reading signal first</h2>
      <p className="mt-2 text-sm text-slate-600">
        Compatibility rankings stay quiet until your local profile has something to compare.
        No fake scores.
      </p>
      <ol className="mt-5 space-y-3 text-sm text-slate-700">
        <li className="rounded-xl bg-slate-50 px-4 py-3 ring-1 ring-slate-100">
          <span className="font-medium text-slate-900">1. Log a few books</span>
          <p className="mt-1 text-xs text-slate-500">
            {tasteLogCount === 0
              ? "Your log is empty."
              : `${tasteLogCount} logged — rate a couple for stronger theme signal.`}
          </p>
          <Link href="/explore" className={`mt-2 inline-block ${linkClassName}`}>
            Explore catalog →
          </Link>
        </li>
        <li className="rounded-xl bg-slate-50 px-4 py-3 ring-1 ring-slate-100">
          <span className="font-medium text-slate-900">2. Set preferences</span>
          <p className="mt-1 text-xs text-slate-500">
            Favorite genres, length, pace, or a community rating floor unlock scoring even
            before a long log.
          </p>
          <Link href="/profile#preferences" className={`mt-2 inline-block ${linkClassName}`}>
            Open preferences →
          </Link>
        </li>
        <li className="rounded-xl bg-slate-50 px-4 py-3 ring-1 ring-slate-100">
          <span className="font-medium text-slate-900">3. Come back here</span>
          <p className="mt-1 text-xs text-slate-500">
            Ranked matches appear once any of those signals exist.
          </p>
        </li>
      </ol>
    </section>
  );
}

function RankedMatchCard({
  item,
  selected,
  onSelect,
}: {
  item: RankedCompatibilityItem;
  selected: boolean;
  onSelect: () => void;
}) {
  const { book, result } = item;
  const topReasons = result.reasons.slice(0, 2);
  const compactDims = result.dimensions.filter((dimension) => dimension.id !== "overall");

  return (
    <article
      className={`rounded-xl border p-4 transition-colors ${
        selected
          ? "border-teal-500 bg-teal-50/50 ring-1 ring-teal-200"
          : "border-slate-200 bg-slate-50/60 hover:border-slate-300"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <button type="button" onClick={onSelect} className="min-w-0 flex-1 text-left">
          <h3 className="truncate text-sm font-semibold text-slate-900">{book.title}</h3>
          <p className="text-xs text-slate-600">{book.author}</p>
        </button>
        <p
          className={`shrink-0 text-sm font-semibold tabular-nums ${
            result.overall === null ? "text-slate-400" : "text-teal-800"
          }`}
        >
          {formatCompatibilityPercent(result.overall)}
        </p>
      </div>

      {topReasons.length > 0 ? (
        <ul className="mt-3 flex flex-wrap gap-1.5">
          {topReasons.map((reason) => (
            <li
              key={reason}
              className="max-w-full truncate rounded-full bg-white px-2.5 py-0.5 text-[11px] font-medium text-slate-700 ring-1 ring-slate-200"
              title={reason}
            >
              {reason}
            </li>
          ))}
        </ul>
      ) : null}

      <dl className="mt-3 grid grid-cols-2 gap-1.5 sm:grid-cols-4">
        {compactDims.map((dimension) => (
          <div
            key={dimension.id}
            className="rounded-lg bg-white px-2 py-1.5 ring-1 ring-slate-100"
          >
            <dt className="truncate text-[10px] font-medium uppercase tracking-wide text-slate-400">
              {dimension.label}
            </dt>
            <dd className="text-xs font-medium tabular-nums text-slate-700">
              {dimension.score === null ? "—" : `${dimension.score}%`}
            </dd>
          </div>
        ))}
      </dl>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button type="button" onClick={onSelect} className={linkClassName}>
          View breakdown
        </button>
        <Link href={`/books/${book.id}`} className={linkClassName}>
          Open book →
        </Link>
      </div>
    </article>
  );
}

function SelectedBookPanel({
  selectedBook,
  result,
}: {
  selectedBook: Book | undefined;
  result: CompatibilityResult | null;
}) {
  if (!selectedBook) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-200 bg-white/70 p-5">
        <h2 className="text-sm font-semibold text-slate-900">Selected match</h2>
        <p className="mt-2 text-sm text-slate-500">
          Pick a ranked book to see the full compatibility breakdown.
        </p>
      </section>
    );
  }

  const dimensions = result?.dimensions ?? EMPTY_DIMENSIONS;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">Selected match</h2>
      <p className="mt-2 text-sm font-semibold text-slate-900">{selectedBook.title}</p>
      <p className="text-xs text-slate-600">{selectedBook.author}</p>
      <p
        className={`mt-3 text-lg font-semibold tabular-nums ${
          result?.overall == null ? "text-slate-400" : "text-teal-800"
        }`}
      >
        {formatCompatibilityPercent(result?.overall ?? null)}
      </p>

      <ul className="mt-4 space-y-2">
        {dimensions.map((row) => (
          <li
            key={row.id}
            className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm ring-1 ring-slate-100"
          >
            <span className="text-slate-600">{row.label}</span>
            <span className="font-medium tabular-nums text-slate-900">
              {row.score === null ? "—" : `${row.score}%`}
            </span>
          </li>
        ))}
      </ul>

      {result?.reasons?.length ? (
        <ul className="mt-4 flex flex-wrap gap-1.5">
          {result.reasons.map((reason) => (
            <li
              key={reason}
              className="rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-800 ring-1 ring-teal-100"
            >
              {reason}
            </li>
          ))}
        </ul>
      ) : null}

      <div className="mt-4">
        <LogBookControls book={selectedBook} compact />
      </div>

      <Link href={`/books/${selectedBook.id}`} className={`mt-4 inline-block ${linkClassName}`}>
        Open full book page →
      </Link>
    </section>
  );
}
