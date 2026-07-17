import { Suspense } from "react";

import { CompatibilityPageClient } from "@/components/compatibility-page";
import { EmptyBooksState } from "@/components/empty-books-state";
import { loadBookLensData } from "@/lib/load-booklens-data";
import { pageShellClassName } from "@/lib/ui";

export const revalidate = 300;

export default async function CompatibilityPage() {
  const { data, warning } = await loadBookLensData();

  if (data.books.length === 0) {
    return <EmptyBooksState source={data.source} />;
  }

  return (
    <Suspense
      fallback={
        <div className={`${pageShellClassName} px-4 py-8 text-sm text-ink-faint`}>
          Preparing your matches…
        </div>
      }
    >
      <CompatibilityPageClient data={data} loadWarning={warning} />
    </Suspense>
  );
}
