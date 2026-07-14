"use client";

import { useEffect, useId, useRef, useState } from "react";

export type ConfirmBookAction = "add" | "remove";

export type ConfirmBookActionDialogProps = {
  book: { title: string; author: string };
  action: ConfirmBookAction;
  open: boolean;
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
};

const COPY: Record<
  ConfirmBookAction,
  { heading: string; prompt: string; confirmLabel: string; confirmClassName: string }
> = {
  add: {
    heading: "Add to profile",
    prompt: "Add this book to your profile?",
    confirmLabel: "Add book",
    confirmClassName:
      "rounded-full bg-teal-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60",
  },
  remove: {
    heading: "Remove from profile",
    prompt: "Remove this book from your profile?",
    confirmLabel: "Remove book",
    confirmClassName:
      "rounded-full bg-slate-800 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-60",
  },
};

export function ConfirmBookActionDialog({
  book,
  action,
  open,
  onConfirm,
  onCancel,
}: ConfirmBookActionDialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);
  const pendingRef = useRef(false);
  const onCancelRef = useRef(onCancel);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const copy = COPY[action];

  useEffect(() => {
    onCancelRef.current = onCancel;
  }, [onCancel]);

  useEffect(() => {
    pendingRef.current = pending;
  }, [pending]);

  useEffect(() => {
    if (!open) {
      return;
    }

    previouslyFocusedRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const focusTimer = window.setTimeout(() => {
      confirmRef.current?.focus();
    }, 0);

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        if (!pendingRef.current) {
          onCancelRef.current();
        }
        return;
      }

      if (event.key !== "Tab" || !panelRef.current) {
        return;
      }

      const active = document.activeElement;
      const focusable = [cancelRef.current, confirmRef.current].filter(
        (node): node is HTMLButtonElement =>
          node instanceof HTMLButtonElement && !node.disabled,
      );
      if (focusable.length === 0) {
        if (!panelRef.current.contains(active)) {
          event.preventDefault();
          panelRef.current.focus();
        }
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey) {
        if (active === first || !panelRef.current.contains(active)) {
          event.preventDefault();
          last.focus();
        }
      } else if (active === last || !panelRef.current.contains(active)) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);

    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocusedRef.current?.focus();
      previouslyFocusedRef.current = null;
    };
  }, [open]);

  if (!open) {
    return null;
  }

  async function handleConfirm() {
    if (pendingRef.current) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      await onConfirm();
    } catch {
      setError("Something went wrong. Try again.");
      setPending(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/30"
        aria-label="Dismiss dialog"
        disabled={pending}
        onClick={() => {
          if (!pendingRef.current) {
            onCancel();
          }
        }}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className="relative z-10 w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-5 shadow-lg outline-none"
        tabIndex={-1}
      >
        <h2 id={titleId} className="text-sm font-semibold text-slate-900">
          {copy.heading}
        </h2>
        <div id={descriptionId} className="mt-3">
          <p className="text-sm font-medium text-slate-900">{book.title}</p>
          <p className="mt-0.5 text-xs text-slate-500">{book.author}</p>
          <p className="mt-3 text-sm text-slate-600">{copy.prompt}</p>
        </div>

        {error ? (
          <p className="mt-3 text-xs text-rose-700" role="alert">
            {error}
          </p>
        ) : null}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            ref={cancelRef}
            type="button"
            disabled={pending}
            onClick={onCancel}
            className="rounded-full bg-white px-4 py-2 text-sm font-medium text-slate-600 ring-1 ring-slate-200 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            ref={confirmRef}
            type="button"
            disabled={pending}
            onClick={() => {
              void handleConfirm();
            }}
            className={copy.confirmClassName}
          >
            {pending ? "Working…" : copy.confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
