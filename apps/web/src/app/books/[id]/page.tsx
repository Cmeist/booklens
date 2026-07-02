import Link from "next/link";
import { notFound } from "next/navigation";

import { BookDetailContent } from "@/components/book-lens-shell";
import { getBookById, getRecommendationsWithBooks } from "@/lib/booklens-data";
import { loadBookLensData } from "@/lib/load-booklens-data";

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
    <div className="min-h-full bg-[#f4f1ea] text-slate-900">
      {warning ? (
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 sm:px-6 lg:px-8">
          {warning}
        </div>
      ) : null}

      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <Link
            href="/"
            className="text-sm font-medium text-teal-700 hover:text-teal-800"
          >
            ← Back to explorer
          </Link>
          <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800 ring-1 ring-teal-100">
            Data: {dataSourceLabel}
          </span>
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
