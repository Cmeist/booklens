import Link from "next/link";
import type { ReactNode } from "react";

import {
  buildAnalyticsSnapshot,
  normalizeScatterX,
  normalizeScatterY,
  type CoverageMetric,
  type RatedBookPoint,
} from "@/lib/analytics";
import type { BookLensDataSource } from "@/lib/booklens-data";
import { formatCoverageLabel } from "@/lib/home-summary";
import type { Book, BookRecommendation } from "@/lib/types";
import { dataBadgeClassName, linkClassName } from "@/lib/ui";

function UnavailableChart({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-rule bg-paper-deep/45 px-4 py-6 text-sm text-ink-soft">
      {message}
    </div>
  );
}

function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`reading-room-card rounded-2xl p-5 ${className}`}>
      {children}
    </div>
  );
}

function BarList({
  items,
  valueKey,
  labelKey,
  barClassName,
}: {
  items: Array<Record<string, string | number>>;
  valueKey: string;
  labelKey: string;
  barClassName: string;
}) {
  const maxValue = Math.max(...items.map((item) => Number(item[valueKey])), 1);

  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={String(item[labelKey])}>
          <div className="flex items-center justify-between gap-3 text-xs text-ink-soft">
            <span className="min-w-0 break-words">{item[labelKey]}</span>
            <span className="shrink-0">{item[valueKey]}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-paper-deep">
            <div
              className={`h-2 rounded-full ${barClassName}`}
              style={{ width: `${(Number(item[valueKey]) / maxValue) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

function CoverageValue({ metric }: { metric: CoverageMetric }) {
  return (
    <dd className="mt-1 text-lg font-semibold text-ink">
      {formatCoverageLabel(metric.percent, metric.known, metric.total)}
    </dd>
  );
}

function ScatterPlot({ points }: { points: RatedBookPoint[] }) {
  const xValues = points.map((point) => point.ratingCount);
  const yValues = points.map((point) => point.averageRating);
  const xMin = Math.min(...xValues);
  const xMax = Math.max(...xValues);
  const yMin = Math.min(...yValues);
  const yMax = Math.max(...yValues);
  const xLabel = "Rating count";
  const yLabel = "Average rating";

  return (
    <div>
      <svg
        viewBox="0 0 100 100"
        className="h-56 w-full rounded-lg bg-paper-deep/45 ring-1 ring-rule/70"
        role="img"
        aria-label={`${xLabel} versus ${yLabel} scatter plot`}
      >
        <line x1="8" y1="92" x2="96" y2="92" className="stroke-rule-strong" strokeWidth="0.5" />
        <line x1="8" y1="8" x2="8" y2="92" className="stroke-rule-strong" strokeWidth="0.5" />
        {points.map((point) => {
          const cx = 8 + (normalizeScatterX(point.ratingCount, xMin, xMax) / 100) * 88;
          const cy = 8 + (normalizeScatterY(point.averageRating, yMin, yMax) / 100) * 84;
          return (
            <g key={point.id}>
              <circle cx={cx} cy={cy} r="2.8" className="fill-forest" />
              <title>{`${point.title}: ${xLabel} ${point.ratingCount}, ${yLabel} ${point.averageRating.toFixed(2)}`}</title>
            </g>
          );
        })}
      </svg>
      <div className="mt-2 flex justify-between gap-3 text-[11px] text-ink-faint">
        <span>
          {xLabel}: {xMin.toLocaleString()} – {xMax.toLocaleString()}
        </span>
        <span>
          {yLabel}: {yMin.toFixed(2)} – {yMax.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

export function AnalyticsSection({
  books,
  recommendations,
  source,
}: {
  books: Book[];
  recommendations: BookRecommendation[];
  source: BookLensDataSource;
}) {
  const analytics = buildAnalyticsSnapshot(books, recommendations);
  const dataSourceLabel = source === "supabase" ? "Supabase" : "Sample fixture";

  return (
    <div className="space-y-10">
      <div className="flex justify-end">
        <span className={dataBadgeClassName}>
          {analytics.bookCount} books · {dataSourceLabel}
        </span>
      </div>

      <section className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-walnut">Collection quality</p>
          <h2 className="mt-1 text-3xl font-semibold text-ink">Data coverage</h2>
          <p className="mt-1 text-sm text-ink-soft">
            How complete the loaded catalog is across key metadata fields.
          </p>
        </div>

        <Panel>
          <h3 className="text-lg font-semibold text-ink">Coverage</h3>
          <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-faint">Rating</dt>
              <CoverageValue metric={analytics.coverage.rating} />
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-faint">
                Page count
              </dt>
              <CoverageValue metric={analytics.coverage.pageCount} />
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-faint">
                Publication year
              </dt>
              <CoverageValue metric={analytics.coverage.publicationYear} />
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-faint">Cover</dt>
              <CoverageValue metric={analytics.coverage.cover} />
            </div>
          </dl>
        </Panel>
      </section>

      <section className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-walnut">Across the shelves</p>
          <h2 className="mt-1 text-3xl font-semibold text-ink">Catalog shape</h2>
          <p className="mt-1 text-sm text-ink-soft">
            Publication decades and how rating volume relates to average rating.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Panel>
            <h3 className="text-lg font-semibold text-ink">Publication decades</h3>
            <div className="mt-3">
              {analytics.canShowDecadeDistribution ? (
                <BarList
                  items={analytics.decadeDistribution.map((item) => ({
                    decade: item.decade,
                    count: item.count,
                  }))}
                  labelKey="decade"
                  valueKey="count"
                  barClassName="bg-walnut"
                />
              ) : (
                <UnavailableChart message="Not enough publication decade metadata to chart a meaningful distribution." />
              )}
            </div>
          </Panel>

          <Panel>
            <h3 className="text-lg font-semibold text-ink">
              Rating count vs average rating
            </h3>
            <div className="mt-3">
              {analytics.canShowRatingCountVsRating ? (
                <>
                  <ScatterPlot points={analytics.ratingCountVsRating.points} />
                  {analytics.ratingCountVsRating.isCapped ? (
                    <p className="mt-2 text-xs text-ink-faint">
                      Showing 40 of {analytics.ratingCountVsRating.totalEligible} books.
                    </p>
                  ) : null}
                </>
              ) : (
                <UnavailableChart message="Need at least two books with both rating count and average rating to plot this chart." />
              )}
            </div>
          </Panel>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-walnut">What rises to the top</p>
          <h2 className="mt-1 text-3xl font-semibold text-ink">Discovery signals</h2>
          <p className="mt-1 text-sm text-ink-soft">
            Recommendation coverage, common similarity reasons, and high average rating with lower
            rating count.
          </p>
        </div>

        <Panel>
          <h3 className="text-lg font-semibold text-ink">Recommendations &amp; gems</h3>

          <div className="mt-4 space-y-6">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">
                Recommendation coverage
              </p>
              <p className="mt-1 text-lg font-semibold text-ink">
                {formatCoverageLabel(
                  analytics.recommendationCoverage.percent,
                  analytics.recommendationCoverage.known,
                  analytics.recommendationCoverage.total,
                )}
              </p>
              <p className="mt-1 text-xs text-ink-faint">
                Distinct source books with at least one valid recommendation.
              </p>
            </div>

            <div>
              <p className="text-sm font-semibold text-ink">Reason frequency</p>
              <div className="mt-3">
                {analytics.canShowReasonFrequency ? (
                  <BarList
                    items={analytics.reasonFrequency.map((item) => ({
                      reason: item.reason,
                      count: item.count,
                    }))}
                    labelKey="reason"
                    valueKey="count"
                    barClassName="bg-forest"
                  />
                ) : (
                  <UnavailableChart message="No recommendation reasons available in the current dataset." />
                )}
              </div>
            </div>

            <div>
              <p className="text-sm font-semibold text-ink">Hidden gems</p>
              <p className="mt-1 text-xs text-ink-faint">
                High average rating with lower rating count among books with at least three ratings.
              </p>
              <div className="mt-3">
                {analytics.canShowHiddenGems ? (
                  <ul className="space-y-2">
                    {analytics.hiddenGems.map((gem) => (
                      <li
                        key={gem.id}
                        className="flex flex-col gap-0.5 text-sm sm:flex-row sm:items-baseline sm:justify-between sm:gap-3"
                      >
                        <Link href={`/books/${gem.id}`} className={linkClassName}>
                          <span className="break-words">{gem.title}</span>
                        </Link>
                        <span className="shrink-0 text-xs text-ink-faint">
                          {gem.averageRating.toFixed(2)} · {gem.ratingCount.toLocaleString()}{" "}
                          ratings
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <UnavailableChart message="No hidden gems match the current thresholds." />
                )}
              </div>
            </div>
          </div>
        </Panel>
      </section>
    </div>
  );
}
