"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  ConfirmBookActionDialog,
  type ConfirmBookAction,
} from "@/components/confirm-book-action-dialog";
import { StarRatingInput } from "@/components/star-rating-input";
import { useUserProfile } from "@/hooks/use-user-profile";
import type { Book } from "@/lib/types";
import { linkClassName } from "@/lib/ui";
import {
  getLogEntry,
  LOG_STATUS_LABELS,
  removeLogEntry,
  upsertLogEntry,
  type LogStatus,
} from "@/lib/user-profile";

type LogBookControlsProps = {
  book: Pick<Book, "id" | "title" | "author">;
  compact?: boolean;
};

const statuses: LogStatus[] = ["want", "reading", "read"];

export function LogBookControls({ book, compact = false }: LogBookControlsProps) {
  const { profile, setProfile, hydrated } = useUserProfile();
  const entry = getLogEntry(profile, book.id);
  const [confirmAction, setConfirmAction] = useState<ConfirmBookAction | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!statusMessage) {
      return;
    }
    const timer = window.setTimeout(() => setStatusMessage(null), 2500);
    return () => window.clearTimeout(timer);
  }, [statusMessage]);

  if (!hydrated) {
    return (
      <p className="text-xs text-ink-faint">
        {compact ? "…" : "Loading profile…"}
      </p>
    );
  }

  function logAs(status: LogStatus) {
    setProfile((current) => upsertLogEntry(current, { bookId: book.id, status }));
  }

  function setRating(rating: number) {
    setProfile((current) =>
      upsertLogEntry(current, {
        bookId: book.id,
        status: getLogEntry(current, book.id)?.status ?? "read",
        rating: rating === 0 ? null : rating,
      }),
    );
  }

  function handleConfirm() {
    if (confirmAction === "add") {
      setProfile((current) => {
        if (getLogEntry(current, book.id)) {
          return current;
        }
        return upsertLogEntry(current, { bookId: book.id, status: "want" });
      });
      setStatusMessage("Added to profile");
    } else if (confirmAction === "remove") {
      setProfile((current) => removeLogEntry(current, book.id));
      setStatusMessage("Removed from profile");
    }
    setConfirmAction(null);
  }

  const dialog =
    confirmAction !== null ? (
      <ConfirmBookActionDialog
        key={`${confirmAction}-${book.id}`}
        book={book}
        action={confirmAction}
        open
        onConfirm={handleConfirm}
        onCancel={() => setConfirmAction(null)}
      />
    ) : null;

  const statusNote = statusMessage ? (
    <p className="text-xs text-forest" role="status">
      {statusMessage}
    </p>
  ) : null;

  if (!entry) {
    return (
      <>
        <div className={compact ? "flex flex-wrap items-center gap-2" : "mt-4 flex flex-wrap items-center gap-3"}>
          <button
            type="button"
            onClick={() => setConfirmAction("add")}
            className="rounded-full border px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition-[filter] hover:brightness-90"
            style={{
              backgroundColor: "var(--forest, #234b3b)",
              borderColor: "var(--forest-deep, #17382c)",
            }}
          >
            Log book
          </button>
          <Link href={`/compatibility?book=${book.id}`} className={linkClassName}>
            See match
          </Link>
          {statusNote}
        </div>
        {dialog}
      </>
    );
  }

  return (
    <>
      <div className={compact ? "space-y-2" : "mt-4 space-y-3"}>
        <div className="flex flex-wrap items-center gap-2">
          <div
            className="inline-flex overflow-hidden rounded-lg ring-1 ring-rule"
            role="group"
            aria-label="Reading status"
          >
            {statuses.map((status, index) => (
              <button
                key={status}
                type="button"
                onClick={() => logAs(status)}
                className={`px-2.5 py-1 text-[11px] font-medium transition-colors ${
                  index > 0 ? "border-l border-rule" : ""
                } ${
                  entry.status === status
                    ? "bg-forest text-white"
                    : "bg-paper-raised text-ink-soft hover:bg-paper-deep"
                }`}
              >
                {LOG_STATUS_LABELS[status]}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setConfirmAction("remove")}
            className="rounded-full bg-paper-raised px-2.5 py-1 text-xs font-medium text-ink-soft ring-1 ring-rule transition-colors hover:bg-paper-deep"
          >
            Remove
          </button>
          <Link href={`/compatibility?book=${book.id}`} className={linkClassName}>
            See match
          </Link>
          {statusNote}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">
            Your rating
          </span>
          <StarRatingInput
            value={entry.rating}
            onChange={setRating}
            size={compact ? "sm" : "md"}
          />
        </div>
      </div>
      {dialog}
    </>
  );
}
