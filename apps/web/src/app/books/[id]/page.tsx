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

      <div className={`${contentContainerClassName} max-w-4xl py-8 sm:py-12`}>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <Link href="/explore" className={linkClassName}>
            ← Back to Discover
          </Link>
          <span className={dataBadgeClassName}>Data: {dataSourceLabel}</span>
        </div>

        <section className="reading-room-card rounded-2xl p-5 sm:p-8">
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
