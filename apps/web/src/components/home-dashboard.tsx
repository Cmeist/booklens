import Link from "next/link";

import { BookCover } from "@/components/book-cover";
import { HomeProfileSnapshot } from "@/components/home-profile-snapshot";
import { HomeTopMatches } from "@/components/home-top-matches";
import type { BookLensData } from "@/lib/booklens-data";
import { CARD_TAGS_MAX, truncateTags } from "@/lib/display-tags";
import { formatRating, formatYear } from "@/lib/format";
import {
  buildCatalogSummary,
  formatCoverageLabel,
  selectFeaturedBooks,
} from "@/lib/home-summary";
import {
  buttonPrimaryClassName,
  contentContainerClassName,
  dataBadgeClassName,
  linkClassName,
  pageShellClassName,
  warningBannerClassName,
} from "@/lib/ui";

type HomeDashboardProps = {
  data: BookLensData;
  loadWarning?: string;
};

const secondaryActionClassName =
  "inline-flex items-center justify-center rounded-full border border-rule-strong bg-paper-raised px-4 py-2 text-sm font-semibold text-ink transition-colors hover:border-walnut hover:bg-walnut-soft/50 hover:text-walnut-deep";

export function HomeDashboard({ data, loadWarning }: HomeDashboardProps) {
  const summary = buildCatalogSummary(data);
  const highlights = selectFeaturedBooks(data.books, 3);

  return (
    <div className={pageShellClassName}>
      {loadWarning ? (
        <div className={warningBannerClassName} role="status">
          {loadWarning}
        </div>
      ) : null}

      <div className={`${contentContainerClassName} space-y-10 py-8 sm:space-y-12 sm:py-12`}>
        <header className="grid gap-7 border-b border-rule pb-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end lg:pb-10">
          <div className="max-w-3xl">
            <p className="editorial-rule max-w-sm text-xs font-semibold uppercase tracking-[0.2em] text-walnut">
              The curated reading room
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-[0.98] tracking-[-0.025em] text-ink sm:text-6xl">
              Find your next remarkable book.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-ink-soft sm:text-lg">
              Explore a thoughtful catalog, keep a private reading record, and see
              why each recommendation belongs on your shelf.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 lg:max-w-xs lg:justify-end">
            <span className={dataBadgeClassName}>Data: {summary.dataSourceLabel}</span>
            <span className={`${dataBadgeClassName} bg-walnut-soft text-walnut-deep ring-walnut/10`}>
              {summary.totalBooks} books loaded
            </span>
          </div>
        </header>

        <section aria-label="Primary actions" className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <Link href="/explore" className={buttonPrimaryClassName}>
            Discover books
          </Link>
          <Link href="/compatibility" className={secondaryActionClassName}>
            See your matches
          </Link>
          <Link href="/profile" className={secondaryActionClassName}>
            Update your library
          </Link>
          <Link href="/analytics" className={`sm:ml-1 ${linkClassName}`}>
            Reading insights
          </Link>
        </section>

        <section
          aria-label="Catalog summary"
          className="reading-room-card rounded-2xl p-5 sm:p-6"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-2xl font-semibold text-ink">Inside the catalog</h2>
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-walnut">
              Collection notes
            </span>
          </div>
          <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="border-l-2 border-forest pl-3">
              <dt className="text-xs text-ink-faint">Books</dt>
              <dd className="mt-0.5 text-base font-semibold text-ink">
                {summary.totalBooks.toLocaleString()}
              </dd>
            </div>
            <div className="border-l border-rule pl-3">
              <dt className="text-xs text-ink-faint">Source</dt>
              <dd className="mt-0.5 text-sm font-medium text-ink">
                {summary.dataSourceLabel}
              </dd>
            </div>
            <div className="border-l border-rule pl-3">
              <dt className="text-xs text-ink-faint">Rating coverage</dt>
              <dd className="mt-0.5 text-sm font-medium text-ink">
                {formatCoverageLabel(
                  summary.ratingCoveragePercent,
                  summary.ratedCount,
                  summary.totalBooks,
                )}
              </dd>
            </div>
            <div className="border-l border-rule pl-3">
              <dt className="text-xs text-ink-faint">Page-count coverage</dt>
              <dd className="mt-0.5 text-sm font-medium text-ink">
                {formatCoverageLabel(
                  summary.pageCountCoveragePercent,
                  summary.pageCountKnownCount,
                  summary.totalBooks,
                )}
              </dd>
            </div>
          </dl>

          <div className="mt-5 border-t border-rule pt-4">
            <p className="text-xs text-ink-faint">Popular shelves</p>
            {summary.topTags.length > 0 ? (
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {summary.topTags.map((item) => (
                  <span
                    key={item.tag}
                    className="rounded-full bg-paper-deep px-2.5 py-0.5 text-[11px] font-medium text-ink-soft ring-1 ring-rule/60"
                  >
                    {item.tag}
                    <span className="ml-1 text-walnut">{item.bookCount}</span>
                  </span>
                ))}
              </div>
            ) : (
              <p className="mt-1 text-sm text-ink-faint">No displayable tags yet.</p>
            )}
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <HomeProfileSnapshot books={data.books} />
          <HomeTopMatches books={data.books} />
        </div>

        {highlights.length > 0 ? (
          <section aria-label="Featured books">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-walnut">From the shelves</p>
                <h2 className="mt-1 text-3xl font-semibold text-ink">Featured books</h2>
                <p className="mt-1 text-sm text-ink-soft">
                  Strong community ratings from the loaded catalog.
                </p>
              </div>
              <Link href="/explore" className={linkClassName}>
                Browse all
              </Link>
            </div>

            <ul className="mt-5 grid gap-4 md:grid-cols-3">
              {highlights.map((book) => {
                const { visible, overflow } = truncateTags(book.tags, CARD_TAGS_MAX);
                return (
                  <li key={book.id} className="reading-room-card rounded-2xl p-4">
                    <div className="flex gap-4">
                      <BookCover book={book} size="md" />
                      <div className="min-w-0">
                        <Link
                          href={`/books/${book.id}`}
                          className="text-lg font-semibold leading-tight text-ink transition-colors hover:text-forest"
                        >
                          <span className="break-words">{book.title}</span>
                        </Link>
                        <p className="mt-1 text-xs text-ink-soft">{book.author}</p>
                        {visible.length > 0 ? (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {visible.map((tag) => (
                              <span
                                key={tag}
                                className="rounded-full bg-paper-deep px-2 py-0.5 text-[10px] font-medium text-ink-soft"
                              >
                                {tag}
                              </span>
                            ))}
                            {overflow > 0 ? (
                              <span className="rounded-full bg-paper-raised px-2 py-0.5 text-[10px] font-medium text-ink-faint ring-1 ring-rule">
                                +{overflow}
                              </span>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                      <div className="mt-3 flex gap-3 border-t border-rule pt-3 text-xs text-ink-faint">
                        <p>{formatYear(book.publicationYear, book.decade)}</p>
                        <p className="text-walnut">{formatRating(book.averageRating)}</p>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  );
}
