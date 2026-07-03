import Link from "next/link";
import { notFound } from "next/navigation";

import { BookDetailContent } from "@/components/book-lens-shell";
import { getBookById, getRecommendationsWithBooks } from "@/lib/booklens-data";
import { loadBookLensData } from "@/lib/load-booklens-data";
import {
  contentContainerClassName,
  dataBadgeClassName,
  linkClassName,
  pageShellClassName,
  warningBannerClassName,
} from "@/lib/ui";

export const revalidate = 300;

type BookDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function BookDetailPage({ params }: BookDetailPageProps) {
  const { id } = await params;
  const { data, warning } = await loadBookLensData();
  const book = getBookById(data.books, id);

  if (!book) {
    notFound();
  }

  const recommendationPairs = getRecommendationsWithBooks(
    data.books,
    data.recommendations,
    book.id,
  );

  const dataSourceLabel = data.source === "supabase" ? "Supabase" : "Sample fixture";

  return (
    <div className={pageShellClassName}>
      {warning ? (
        <div className={warningBannerClassName} role="status">
          {warning}
        </div>
      ) : null}

      <div className={`${contentContainerClassName} max-w-4xl py-8`}>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">BookLens</p>
        <div className="mt-4 mb-6 flex flex-wrap items-center justify-between gap-3">
          <Link href="/" className={linkClassName}>
            ← Back to explorer
          </Link>
          <span className={dataBadgeClassName}>Data: {dataSourceLabel}</span>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <BookDetailContent
            book={book}
            recommendationPairs={recommendationPairs}
            mode="page"
          />
        </section>
      </div>
    </div>
  );
}
