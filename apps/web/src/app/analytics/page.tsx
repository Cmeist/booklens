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

      <div className={`${contentContainerClassName} py-8 sm:py-12`}>
        <header className="mb-8 max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-walnut">
            A closer look at the collection
          </p>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            Insights
          </h1>
          <p className="mt-2 text-sm leading-6 text-ink-soft">
            Catalog coverage, publication shape, and recommendation discovery signals for the loaded
            dataset.
          </p>
        </header>

        <AnalyticsSection
          books={data.books}
          recommendations={data.recommendations}
          source={data.source}
        />
      </div>
    </div>
  );
}
