"use client";

import { useId, useState } from "react";

type StarRatingInputProps = {
  value: number | null;
  onChange: (rating: number) => void;
  size?: "sm" | "md";
};

const STAR_PATH =
  "M12 2.5l2.72 5.51 6.08.89-4.4 4.29 1.04 6.06L12 16.4l-5.44 2.85 1.04-6.06-4.4-4.29 6.08-.89L12 2.5z";

function formatValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function StarIcon({
  filled,
  sizePx,
  clipId,
}: {
  filled: "empty" | "half" | "full";
  sizePx: number;
  clipId: string;
}) {
  return (
    <svg
      width={sizePx}
      height={sizePx}
      viewBox="0 0 24 24"
      className="block"
      aria-hidden="true"
    >
      <defs>
        <clipPath id={clipId}>
          <rect x="0" y="0" width="12" height="24" />
        </clipPath>
      </defs>
      <path d={STAR_PATH} className="fill-paper-deep" />
      {filled === "full" ? (
        <path d={STAR_PATH} className="fill-walnut" />
      ) : null}
      {filled === "half" ? (
        <path d={STAR_PATH} className="fill-walnut" clipPath={`url(#${clipId})`} />
      ) : null}
    </svg>
  );
}

export function StarRatingInput({
  value,
  onChange,
  size = "md",
}: StarRatingInputProps) {
  const reactId = useId().replace(/:/g, "");
  const [hoverValue, setHoverValue] = useState<number | null>(null);
  const displayValue = hoverValue ?? value;
  const sizePx = size === "sm" ? 18 : 22;

  function fillFor(star: number): "empty" | "half" | "full" {
    if (displayValue === null) {
      return "empty";
    }
    if (displayValue >= star) {
      return "full";
    }
    if (displayValue >= star - 0.5) {
      return "half";
    }
    return "empty";
  }

  return (
    <div
      className="inline-flex items-center gap-1.5"
      role="group"
      aria-label="Personal rating"
      onMouseLeave={() => setHoverValue(null)}
    >
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => {
          const halfThreshold = star - 0.5;
          const fullThreshold = star;

          return (
            <span
              key={star}
              className="relative inline-flex shrink-0"
              style={{ width: sizePx, height: sizePx }}
            >
              <button
                type="button"
                className="absolute inset-y-0 left-0 z-10 w-1/2 cursor-pointer rounded-l-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-walnut"
                aria-label={`Rate ${halfThreshold} stars`}
                title={`${halfThreshold}★`}
                onMouseEnter={() => setHoverValue(halfThreshold)}
                onFocus={() => setHoverValue(halfThreshold)}
                onBlur={() => setHoverValue(null)}
                onClick={() => onChange(halfThreshold)}
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 z-10 w-1/2 cursor-pointer rounded-r-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-walnut"
                aria-label={`Rate ${fullThreshold} stars`}
                title={`${fullThreshold}★`}
                onMouseEnter={() => setHoverValue(fullThreshold)}
                onFocus={() => setHoverValue(fullThreshold)}
                onBlur={() => setHoverValue(null)}
                onClick={() => onChange(fullThreshold)}
              />
              <StarIcon
                filled={fillFor(star)}
                sizePx={sizePx}
                clipId={`${reactId}-half-${star}`}
              />
            </span>
          );
        })}
      </div>

      <span
        className={`min-w-[1.75rem] tabular-nums text-xs font-medium ${
          displayValue !== null ? "text-ink-soft" : "text-ink-faint"
        }`}
        aria-live="polite"
      >
        {displayValue !== null ? formatValue(displayValue) : "—"}
      </span>

      {value !== null ? (
        <button
          type="button"
          onClick={() => onChange(0)}
          onMouseEnter={() => setHoverValue(null)}
          className="rounded-full px-2 py-0.5 text-[10px] font-medium text-ink-faint transition-colors hover:bg-paper-deep hover:text-ink"
          aria-label="Clear rating"
        >
          Clear
        </button>
      ) : null}
    </div>
  );
}
