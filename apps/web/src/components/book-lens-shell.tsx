import Link from "next/link";

import { linkClassName } from "@/lib/ui";

import {
  formatPageCount,
  formatRating,
  formatRatingCount,
  formatScore,
  formatYear,
} from "@/lib/format";
import type { Book, BookRecommendation, RecommendationWithBook } from "@/lib/types";

function BookCover({ book, size = "md" }: { book: Book; size?: "sm" | "md" | "lg" }) {
  const sizeClasses = {
    sm: "h-16 w-12 text-xs",
    md: "h-24 w-16 text-sm",
    lg: "h-40 w-28 text-lg",
  }[size];

  if (book.coverUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={book.coverUrl}
        alt={`Cover of ${book.title}`}
        className={`${sizeClasses} shrink-0 rounded-md object-cover shadow-sm ring-1 ring-black/5`}
      />
    );
  }

  const initials = book.title
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();

  return (
    <div
      className={`${sizeClasses} flex shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-teal-700 to-slate-800 font-semibold text-white shadow-sm ring-1 ring-black/5`}
      aria-hidden="true"
    >
      {initials}
    </div>
  );
}

function ReasonChips({ reasons }: { reasons: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {reasons.map((reason) => (
        <span
          key={reason}
          className="rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-800 ring-1 ring-teal-100"
        >
          {reason}
        </span>
      ))}
    </div>
  );
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2 ring-1 ring-slate-100">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </dt>
      <dd className="mt-0.5 text-sm font-medium text-slate-900">{value}</dd>
    </div>
  );
}

function RecommendationCard({
  book,
  recommendation,
  href,
}: {
  book: Book;
  recommendation: BookRecommendation;
  href?: string;
}) {
  const content = (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-slate-300">
      <div className="flex gap-3">
        <BookCover book={book} size="sm" />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h4 className="text-sm font-semibold text-slate-900">{book.title}</h4>
              <p className="text-xs text-slate-600">{book.author}</p>
            </div>
            <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
              {formatScore(recommendation.score)}
            </span>
          </div>
          <div className="mt-3">
            <ReasonChips reasons={recommendation.reasons} />
          </div>
        </div>
      </div>
    </article>
  );

  if (href) {
    return (
      <Link href={href} className="block">
        {content}
      </Link>
    );
  }

  return content;
}

function SimilarBooksSection({
  recommendationPairs,
  linkToDetail = false,
}: {
  recommendationPairs: RecommendationWithBook[];
  linkToDetail?: boolean;
}) {
  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900">Similar books</h3>
        <span className="text-xs text-slate-500">{recommendationPairs.length} matches</span>
      </div>
      <div className="mt-3 space-y-3">
        {recommendationPairs.length > 0 ? (
          recommendationPairs.map(({ recommendation, book: recommendedBook }) => (
            <RecommendationCard
              key={recommendation.similarBookId}
              book={recommendedBook}
              recommendation={recommendation}
              href={linkToDetail ? `/books/${recommendedBook.id}` : undefined}
            />
          ))
        ) : (
          <p className="rounded-lg bg-slate-50 px-3 py-4 text-sm text-slate-500">
            No recommendations available for this book yet.
          </p>
        )}
      </div>
    </div>
  );
}

function BookDetailContent({
  book,
  recommendationPairs,
  mode = "preview",
}: {
  book: Book;
  recommendationPairs: RecommendationWithBook[];
  mode?: "preview" | "page";
}) {
  return (
    <>
      {mode === "preview" ? (
        <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
          Selected book
        </p>
      ) : null}

      <div className={`flex gap-4 ${mode === "preview" ? "mt-4" : "mt-2"}`}>
        <BookCover book={book} size="lg" />
        <div className="min-w-0 flex-1">
          <h2
            className={
              mode === "page"
                ? "text-2xl font-semibold text-slate-900 sm:text-3xl"
                : "text-xl font-semibold text-slate-900"
            }
          >
            {book.title}
          </h2>
          <p className="mt-1 text-sm text-slate-600">{book.author}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {book.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-slate-700">{book.description}</p>

      <dl className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <MetadataItem label="Year" value={formatYear(book.publicationYear, book.decade)} />
        <MetadataItem label="Length" value={formatPageCount(book.pageCount)} />
        <MetadataItem label="Rating" value={formatRating(book.averageRating)} />
        <MetadataItem label="Popularity" value={formatRatingCount(book.ratingCount)} />
      </dl>

      {mode === "page" ? (
        <dl className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <MetadataItem label="Source" value={book.source} />
          <MetadataItem label="Source ID" value={book.sourceId} />
        </dl>
      ) : null}

      <div className="mt-6">
        <SimilarBooksSection
          recommendationPairs={recommendationPairs}
          linkToDetail={mode === "page"}
        />
      </div>

      {mode === "preview" ? (
        <div className="mt-5 space-y-2">
          <Link
            href={`/books/${book.id}`}
            className={linkClassName}
          >
            Open full detail page →
          </Link>
        </div>
      ) : null}
    </>
  );
}

function BookListCard({
  book,
  selected,
  onSelect,
}: {
  book: Book;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <article
      className={`w-full rounded-xl border p-4 transition-colors ${
        selected
          ? "border-teal-500 bg-teal-50/60 shadow-sm ring-1 ring-teal-200"
          : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <div className="flex gap-3">
        <button type="button" onClick={() => onSelect(book.id)} className="flex min-w-0 flex-1 gap-3 text-left">
          <BookCover book={book} size="sm" />
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-sm font-semibold text-slate-900">{book.title}</h3>
            <p className="text-xs text-slate-600">{book.author}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {book.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600"
                >
                  {tag}
                </span>
              ))}
            </div>
            <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-500">
              {book.description}
            </p>
            <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-500">
              <span>{formatYear(book.publicationYear, book.decade)}</span>
              <span>{formatPageCount(book.pageCount)}</span>
              <span>
                {formatRating(book.averageRating)} · {formatRatingCount(book.ratingCount)}
              </span>
            </div>
          </div>
        </button>
      </div>
      <div className="mt-3 flex justify-end">
        <Link
          href={`/books/${book.id}`}
          className={linkClassName}
        >
          Open detail page
        </Link>
      </div>
    </article>
  );
}

function BookDetailPanel({
  book,
  recommendationPairs,
}: {
  book: Book;
  recommendationPairs: RecommendationWithBook[];
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:sticky lg:top-6">
      <BookDetailContent
        book={book}
        recommendationPairs={recommendationPairs}
        mode="preview"
      />
    </section>
  );
}

export {
  BookDetailContent,
  BookDetailPanel,
  BookListCard,
  ReasonChips,
};
