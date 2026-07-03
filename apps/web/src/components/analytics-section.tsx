import {
  buildAnalyticsSnapshot,
  normalizeScatterX,
  normalizeScatterY,
  type RatedBookPoint,
  type TagRatingAverage,
} from "@/lib/analytics";
import type { BookLensDataSource } from "@/lib/booklens-data";
import type { Book, TopTag } from "@/lib/types";

function UnavailableChart({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
      {message}
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-100">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-900">{value}</p>
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
          <div className="flex items-center justify-between text-xs text-slate-600">
            <span>{item[labelKey]}</span>
            <span>{item[valueKey]}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-slate-100">
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

function TagRatingList({ items }: { items: TagRatingAverage[] }) {
  const ratedItems = items.filter((item) => item.hasEnoughRatingData && item.averageRating !== null);
  const maxRating = Math.max(...ratedItems.map((item) => item.averageRating ?? 0), 1);

  return (
    <ul className="space-y-2">
      {ratedItems.map((item) => (
        <li key={item.tag}>
          <div className="flex items-center justify-between text-xs text-slate-600">
            <span>{item.tag}</span>
            <span>
              {item.averageRating?.toFixed(2)} · {item.ratedBookCount} rated
            </span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-slate-100">
            <div
              className="h-2 rounded-full bg-violet-500"
              style={{ width: `${((item.averageRating ?? 0) / maxRating) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

function ScatterPlot({
  points,
  xValue,
  xLabel,
  yLabel,
}: {
  points: RatedBookPoint[];
  xValue: (point: RatedBookPoint) => number;
  xLabel: string;
  yLabel: string;
}) {
  const xValues = points.map(xValue);
  const yValues = points.map((point) => point.averageRating);
  const xMin = Math.min(...xValues);
  const xMax = Math.max(...xValues);
  const yMin = Math.min(...yValues);
  const yMax = Math.max(...yValues);

  return (
    <div>
      <div className="overflow-x-auto">
        <svg viewBox="0 0 100 100" className="h-56 w-full min-w-[280px] rounded-lg bg-slate-50 ring-1 ring-slate-100">
          <line x1="8" y1="92" x2="96" y2="92" className="stroke-slate-300" strokeWidth="0.5" />
          <line x1="8" y1="8" x2="8" y2="92" className="stroke-slate-300" strokeWidth="0.5" />
          {points.map((point) => {
            const cx = 8 + (normalizeScatterX(xValue(point), xMin, xMax) / 100) * 88;
            const cy = 8 + (normalizeScatterY(point.averageRating, yMin, yMax) / 100) * 84;
            return (
              <g key={point.id}>
                <circle cx={cx} cy={cy} r="2.8" className="fill-teal-600" />
                <title>
                  {point.title}: {xLabel} {xValue(point)}, {yLabel} {point.averageRating.toFixed(2)}
                </title>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="mt-2 flex justify-between text-[11px] text-slate-500">
        <span>
          {xLabel}: {xMin.toLocaleString()} – {xMax.toLocaleString()}
        </span>
        <span>
          {yLabel}: {yMin.toFixed(2)} – {yMax.toFixed(2)}
        </span>
      </div>
      <ul className="mt-3 space-y-1 text-xs text-slate-600">
        {points.map((point) => (
          <li key={point.id}>
            {point.title}: {xLabel} {xValue(point).toLocaleString()}, {yLabel}{" "}
            {point.averageRating.toFixed(2)}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AnalyticsSection({
  books,
  topTags,
  source,
}: {
  books: Book[];
  topTags: TopTag[];
  source: BookLensDataSource;
}) {
  const analytics = buildAnalyticsSnapshot(books, topTags);
  const dataSourceLabel = source === "supabase" ? "Supabase" : "Sample fixture";

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Analytics</h2>
          <p className="mt-1 text-sm text-slate-600">
            Dataset summaries from {dataSourceLabel.toLowerCase()} data. Sparse metadata shows
            honest unavailable states instead of misleading charts.
          </p>
        </div>
        <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800 ring-1 ring-teal-100">
          {analytics.bookCount} books
        </span>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-4">
        <SummaryCard label="Books" value={analytics.bookCount.toString()} />
        <SummaryCard
          label="Avg. rating"
          value={analytics.averageRating !== null ? analytics.averageRating.toFixed(2) : "N/A"}
        />
        <SummaryCard
          label="Avg. page count"
          value={
            analytics.averagePageCount !== null ? analytics.averagePageCount.toLocaleString() : "N/A"
          }
        />
        <SummaryCard
          label="Rated books"
          value={`${analytics.ratedBookCount} / ${analytics.bookCount}`}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Top tags</h3>
          {analytics.topTags.length > 0 ? (
            <div className="mt-3">
              <BarList
                items={analytics.topTags.slice(0, 10).map((item) => ({
                  tag: item.tag,
                  bookCount: item.bookCount,
                }))}
                labelKey="tag"
                valueKey="bookCount"
                barClassName="bg-teal-600"
              />
            </div>
          ) : (
            <div className="mt-3">
              <UnavailableChart message="No tag data available in the current dataset." />
            </div>
          )}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-900">Publication decades</h3>
          {analytics.canShowDecadeDistribution ? (
            <div className="mt-3">
              <BarList
                items={analytics.decadeDistribution.map((item) => ({
                  decade: item.decade,
                  count: item.count,
                }))}
                labelKey="decade"
                valueKey="count"
                barClassName="bg-amber-500"
              />
            </div>
          ) : (
            <div className="mt-3">
              <UnavailableChart message="Not enough publication decade metadata to chart a meaningful distribution." />
            </div>
          )}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-900">Average rating by tag</h3>
          {analytics.canShowAverageRatingByTag ? (
            <div className="mt-3">
              <TagRatingList items={analytics.averageRatingByTag} />
            </div>
          ) : (
            <div className="mt-3">
              <UnavailableChart message="Need at least two rated books per tag before showing average rating by tag." />
            </div>
          )}
          {analytics.averageRatingByTag.some((item) => !item.hasEnoughRatingData) ? (
            <p className="mt-2 text-xs text-slate-500">
              Tags with fewer than two rated books are hidden to avoid misleading averages.
            </p>
          ) : null}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-900">Page count vs average rating</h3>
          <div className="mt-3">
            {analytics.canShowPageCountVsRating ? (
              <ScatterPlot
                points={analytics.pageCountVsRating}
                xValue={(point) => point.pageCount as number}
                xLabel="Pages"
                yLabel="Rating"
              />
            ) : (
              <UnavailableChart message="Need at least two books with both page count and average rating to plot this chart." />
            )}
          </div>
        </div>

        <div className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-900">Rating count vs average rating</h3>
          <div className="mt-3">
            {analytics.canShowRatingCountVsRating ? (
              <ScatterPlot
                points={analytics.ratingCountVsRating}
                xValue={(point) => point.ratingCount as number}
                xLabel="Ratings"
                yLabel="Avg rating"
              />
            ) : (
              <UnavailableChart message="Need at least two books with both rating count and average rating to plot this chart." />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
