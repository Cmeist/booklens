import { AnalyticsSection } from "@/components/analytics-section";
import { EmptyBooksState } from "@/components/empty-books-state";
import { loadBookLensData } from "@/lib/load-booklens-data";
import { contentContainerClassName, pageShellClassName, warningBannerClassName } from "@/lib/ui";

export const revalidate = 300;

export default async function AnalyticsPage() {
  const { data, warning } = await loadBookLensData();

  if (data.books.length === 0) {
    return <EmptyBooksState source={data.source} />;
  }

  return (
    <div className={pageShellClassName}>
      {warning ? (
        <div className={warningBannerClassName} role="status">
          {warning}
        </div>
      ) : null}

      <div className={`${contentContainerClassName} py-8`}>
        <header className="mb-6 max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
            BookLens
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Analytics
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Dataset summaries and trend views for the loaded catalog.
          </p>
        </header>

        <AnalyticsSection books={data.books} topTags={data.topTags} source={data.source} />
      </div>
    </div>
  );
}
