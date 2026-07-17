"use client";

import Link from "next/link";
import { useMemo } from "react";

import { useUserProfile } from "@/hooks/use-user-profile";
import { effectivePreferredLength } from "@/lib/compatibility";
import { profileHasCompatibilitySignal } from "@/lib/compatibility-rankings";
import { formatPreferredLengthLabel } from "@/lib/home-summary";
import type { Book } from "@/lib/types";
import { deriveTaste } from "@/lib/user-profile";
import { linkClassName } from "@/lib/ui";

type HomeProfileSnapshotProps = {
  books: Book[];
};

export function HomeProfileSnapshot({ books }: HomeProfileSnapshotProps) {
  const { profile, hydrated } = useUserProfile();
  const taste = useMemo(() => deriveTaste(profile, books), [profile, books]);
  const hasProfileSignal = useMemo(
    () => profileHasCompatibilitySignal(profile, books, taste),
    [profile, books, taste],
  );
  const preferredLength = effectivePreferredLength(profile);

  if (!hydrated) {
    return (
      <section
        aria-label="Your profile"
        className="reading-room-card rounded-2xl p-5"
      >
        <h2 className="text-2xl font-semibold text-ink">Your reading profile</h2>
        <p className="mt-2 text-sm text-ink-faint">Loading local profile…</p>
      </section>
    );
  }

  if (!hasProfileSignal) {
    return (
      <section
        aria-label="Your profile"
        className="reading-room-card rounded-2xl p-5"
      >
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-walnut">Private to this browser</p>
        <h2 className="mt-1 text-2xl font-semibold text-ink">Begin your reading profile</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          Log a few books or set preferences to unlock taste tags and compatibility
          matches. Stays in this browser only.
        </p>
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2">
          <Link href="/explore" className={linkClassName}>
            Browse catalog
          </Link>
          <Link href="/profile#preferences" className={linkClassName}>
            Set preferences
          </Link>
        </div>
      </section>
    );
  }

  const tasteTags = taste.topTags.slice(0, 4);

  return (
    <section
      aria-label="Your profile"
      className="reading-room-card rounded-2xl p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="text-2xl font-semibold text-ink">Your reading profile</h2>
        <Link href="/profile" className={linkClassName}>
          Update profile
        </Link>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-xs text-ink-faint">Logged</dt>
          <dd className="mt-0.5 font-semibold text-ink">{taste.logCount}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-faint">Rated</dt>
          <dd className="mt-0.5 font-semibold text-ink">{taste.ratedCount}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs text-ink-faint">Preferred length</dt>
          <dd className="mt-0.5 font-semibold text-ink">
            {formatPreferredLengthLabel(
              preferredLength === "any" ? taste.preferredLength : preferredLength,
            )}
          </dd>
        </div>
      </dl>

      <div className="mt-4">
        <p className="text-xs text-ink-faint">Top taste tags</p>
        {tasteTags.length > 0 ? (
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {tasteTags.map((item) => (
              <span
                key={item.tag}
                className="rounded-full bg-forest-soft px-2 py-0.5 text-[11px] font-medium text-forest"
              >
                {item.tag}
              </span>
            ))}
          </div>
        ) : (
          <p className="mt-1 text-sm text-ink-faint">
            No tags yet — rate logged books or add favorite genres.
          </p>
        )}
      </div>
    </section>
  );
}
