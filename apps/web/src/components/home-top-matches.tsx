"use client";

import Link from "next/link";
import { useMemo } from "react";

import { useUserProfile } from "@/hooks/use-user-profile";
import {
  formatCompatibilityPercent,
  profileHasCompatibilitySignal,
  rankCompatibilityMatches,
  type RankedCompatibilityItem,
} from "@/lib/compatibility-rankings";
import type { Book } from "@/lib/types";
import { deriveTaste } from "@/lib/user-profile";
import { linkClassName } from "@/lib/ui";

const HOME_MATCH_LIMIT = 3;

type HomeTopMatchesProps = {
  books: Book[];
};

export function HomeTopMatches({ books }: HomeTopMatchesProps) {
  const { profile, hydrated } = useUserProfile();

  const taste = useMemo(() => deriveTaste(profile, books), [profile, books]);
  const hasSignal = useMemo(
    () => profileHasCompatibilitySignal(profile, books, taste),
    [profile, books, taste],
  );

  const matches = useMemo((): RankedCompatibilityItem[] => {
    if (!hydrated || !hasSignal) {
      return [];
    }
    return rankCompatibilityMatches(profile, books, {
      hideRead: true,
      sort: "match",
      limit: HOME_MATCH_LIMIT,
      derivedTaste: taste,
    });
  }, [hydrated, hasSignal, profile, books, taste]);

  if (!hydrated || !hasSignal || matches.length === 0) {
    return null;
  }

  return (
    <section
      aria-label="Top matches"
      className="reading-room-card rounded-2xl p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-walnut">Chosen for you</p>
          <h2 className="mt-1 text-2xl font-semibold text-ink">Top matches</h2>
          <p className="mt-1 text-sm text-ink-soft">
            Best unread fits from your local taste profile.
          </p>
        </div>
        <Link href="/compatibility" className={linkClassName}>
          View all matches
        </Link>
      </div>

      <ul className="mt-4 divide-y divide-rule">
        {matches.map(({ book, result }) => {
          const reason = result.reasons[0];
          return (
            <li key={book.id} className="py-3 first:pt-0 last:pb-0">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <Link
                    href={`/books/${book.id}`}
                    className="text-base font-semibold text-ink transition-colors hover:text-forest"
                  >
                    <span className="break-words">{book.title}</span>
                  </Link>
                  <p className="mt-0.5 text-xs text-ink-soft">{book.author}</p>
                  {reason ? (
                    <span
                      className="mt-2 inline-block max-w-full truncate rounded-full bg-forest-soft px-2 py-0.5 text-[11px] font-medium text-forest"
                      title={reason}
                    >
                      {reason}
                    </span>
                  ) : null}
                </div>
                <p
                  className={`shrink-0 text-sm font-semibold tabular-nums ${
                    result.overall === null ? "text-ink-faint" : "text-forest"
                  }`}
                >
                  {formatCompatibilityPercent(result.overall)}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
