import Link from "next/link";

import { BookCover } from "@/components/book-cover";
import { BookTags } from "@/components/book-tags";
import { LogBookControls } from "@/components/log-book-controls";
import { ThemeProfile } from "@/components/theme-profile";
import { CARD_TAGS_MAX, truncateTags } from "@/lib/display-tags";
import {
  formatPageLength,
  formatRating,
  formatRatingCount,
  formatScore,
  formatYear,
} from "@/lib/format";
import type { Book, BookRecommendation, RecommendationWithBook } from "@/lib/types";
import { linkClassName } from "@/lib/ui";

function ReasonChips({ reasons }: { reasons: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {reasons.map((reason) => (
        <span
          key={reason}
          className="rounded-full bg-forest-soft px-2.5 py-0.5 text-xs font-medium text-forest ring-1 ring-forest/10"
        >
          {reason}
        </span>
      ))}
    </div>
  );
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-paper-deep/55 px-3 py-2 ring-1 ring-rule/70">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">
        {label}
      </dt>
      <dd className="mt-0.5 text-sm font-medium text-ink">{value}</dd>
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
    <article className="reading-room-card rounded-xl p-4 transition-colors hover:border-rule-strong">
      <div className="flex gap-3">
        <BookCover book={book} size="sm" />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h4 className="text-base font-semibold text-ink">{book.title}</h4>
              <p className="text-xs text-ink-soft">{book.author}</p>
            </div>
            <span className="shrink-0 rounded-full bg-walnut-soft px-2 py-0.5 text-[11px] font-semibold text-walnut-deep">
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
        <h3 className="text-lg font-semibold text-ink">Similar books</h3>
        <span className="text-xs text-ink-faint">{recommendationPairs.length} matches</span>
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
          <p className="rounded-lg bg-paper-deep/55 px-3 py-4 text-sm text-ink-faint">
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
        <p className="editorial-rule text-xs font-semibold uppercase tracking-[0.16em] text-walnut">
          Selected book
        </p>
      ) : null}

      <div className={`flex gap-4 ${mode === "preview" ? "mt-4" : "mt-2"}`}>
        <BookCover book={book} size="lg" />
        <div className="min-w-0 flex-1">
          <h2
            className={
              mode === "page"
                ? "text-3xl font-semibold text-ink sm:text-4xl"
                : "text-2xl font-semibold text-ink"
            }
          >
            {book.title}
          </h2>
          <p className="mt-1 text-sm text-ink-soft">{book.author}</p>
          <BookTags tags={book.tags} mode={mode} />
        </div>
      </div>

      <p className="mt-4 text-sm leading-7 text-ink-soft">{book.description}</p>

      <dl className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <MetadataItem label="Year" value={formatYear(book.publicationYear, book.decade)} />
        <MetadataItem label="Length" value={formatPageLength(book.pageCount)} />
        <MetadataItem label="Rating" value={formatRating(book.averageRating)} />
        <MetadataItem label="Popularity" value={formatRatingCount(book.ratingCount)} />
      </dl>

      {mode === "page" ? (
        <details className="group mt-3 rounded-lg border border-rule bg-paper-raised px-3 py-2">
          <summary className="cursor-pointer text-xs font-semibold text-ink-soft marker:text-walnut">
            Catalog source details
          </summary>
          <dl className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <MetadataItem label="Source" value={book.source} />
            <MetadataItem label="Source ID" value={book.sourceId} />
          </dl>
        </details>
      ) : null}

      <LogBookControls book={book} />

      <ThemeProfile book={book} maxRows={mode === "preview" ? 5 : undefined} />

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

function CardTags({ tags }: { tags: string[] }) {
  const { visible, overflow } = truncateTags(tags, CARD_TAGS_MAX);
  if (visible.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 flex flex-wrap gap-1">
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
          +{overflow} more
        </span>
      ) : null}
    </div>
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
          ? "border-forest bg-forest-soft/65 shadow-sm ring-1 ring-forest/20"
          : "border-rule bg-paper-raised hover:border-rule-strong hover:bg-paper-deep/35"
      }`}
    >
      <div className="flex gap-3">
        <button type="button" onClick={() => onSelect(book.id)} className="flex min-w-0 flex-1 gap-3 text-left">
          <BookCover book={book} size="sm" />
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-base font-semibold text-ink">{book.title}</h3>
            <p className="text-xs text-ink-soft">{book.author}</p>
            <CardTags tags={book.tags} />
            <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-ink-faint">
              {book.description}
            </p>
            <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-ink-faint">
              <span>{formatYear(book.publicationYear, book.decade)}</span>
              <span>{formatPageLength(book.pageCount)}</span>
              <span>
                {formatRating(book.averageRating)} · {formatRatingCount(book.ratingCount)}
              </span>
            </div>
          </div>
        </button>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-end gap-3">
        <LogBookControls book={book} compact />
        <Link href={`/books/${book.id}`} className={linkClassName}>
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
    <section className="reading-room-card rounded-2xl p-5 lg:sticky lg:top-24">
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
