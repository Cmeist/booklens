import Link from "next/link";

import type { BookLensData } from "@/lib/booklens-data";
import { formatRating, formatYear } from "@/lib/format";
import {
  buttonPrimaryClassName,
  contentContainerClassName,
  dataBadgeClassName,
  linkClassName,
  pageShellClassName,
  warningBannerClassName,
} from "@/lib/ui";

type HomeDashboardProps = {
  data: BookLensData;
  loadWarning?: string;
};

function featuredBooks(data: BookLensData) {
  const rated = data.books
    .filter((book) => book.averageRating !== null)
    .sort((left, right) => (right.averageRating ?? 0) - (left.averageRating ?? 0));

  if (rated.length >= 3) {
    return rated.slice(0, 3);
  }

  return data.books.slice(0, 3);
}

const entryPoints = [
  {
    href: "/explore",
    title: "Explore",
    description: "Search and filter the catalog with tags, decades, and ratings.",
  },
  {
    href: "/compatibility",
    title: "Compatibility",
    description: "Compare books against your reading profile.",
  },
  {
    href: "/analytics",
    title: "Analytics",
    description: "Dataset trends, tag distribution, and rating summaries.",
  },
] as const;

export function HomeDashboard({ data, loadWarning }: HomeDashboardProps) {
  const { books, source } = data;
  const dataSourceLabel = source === "supabase" ? "Supabase" : "Sample fixture";
  const highlights = featuredBooks(data);

  return (
    <div className={pageShellClassName}>
      {loadWarning ? (
        <div className={warningBannerClassName} role="status">
          {loadWarning}
        </div>
      ) : null}

      <div className={`${contentContainerClassName} py-8 sm:py-10`}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
              BookLens
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
              Book discovery dashboard
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              Filter a curated catalog, inspect explainable similar-book recommendations, and
              review dataset trends — all from one lightweight data product shell.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className={dataBadgeClassName}>Data: {dataSourceLabel}</span>
            <span className={`${dataBadgeClassName} bg-slate-100 text-slate-600 ring-0`}>
              {books.length} books loaded
            </span>
          </div>
        </div>

        <section aria-label="Entry points" className="mt-8 grid gap-4 sm:grid-cols-3">
          {entryPoints.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="group rounded-xl border border-slate-200 bg-white p-5 transition-colors hover:border-teal-300 hover:bg-teal-50/30"
            >
              <h2 className="text-sm font-semibold text-slate-900 group-hover:text-teal-800">
                {item.title}
              </h2>
              <p className="mt-1 text-sm text-slate-600">{item.description}</p>
              <span className={`mt-4 inline-block ${linkClassName}`}>Open →</span>
            </Link>
          ))}
        </section>

        {highlights.length > 0 ? (
          <section aria-label="Featured books" className="mt-10">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Featured from dataset</h2>
                <p className="mt-1 text-sm text-slate-600">
                  Top-rated titles currently loaded from {dataSourceLabel.toLowerCase()}.
                </p>
              </div>
              <Link href="/explore" className={linkClassName}>
                Browse all books
              </Link>
            </div>

            <ul className="mt-4 divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
              {highlights.map((book) => (
                <li key={book.id} className="px-4 py-4 sm:px-5">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <Link
                        href={`/books/${book.id}`}
                        className="text-sm font-semibold text-slate-900 hover:text-teal-800"
                      >
                        <span className="break-words">{book.title}</span>
                      </Link>
                      <p className="mt-0.5 text-xs text-slate-600">{book.author}</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {book.tags.slice(0, 4).map((tag) => (
                          <span
                            key={tag}
                            className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="shrink-0 text-xs text-slate-500 sm:text-right">
                      <p>{formatYear(book.publicationYear, book.decade)}</p>
                      <p className="mt-0.5">{formatRating(book.averageRating)}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <div className="mt-10">
          <Link href="/explore" className={buttonPrimaryClassName}>
            Start exploring
          </Link>
        </div>
      </div>
    </div>
  );
}
