import {
  scoreThemeProfile,
  selectThemeScoresForDisplay,
  type ThemeScore,
} from "@/lib/theme-profile";
import type { Book } from "@/lib/types";

type ThemeProfileProps = {
  book: Book;
  /** Cap rows (preview). Omit for full 12 on detail page. */
  maxRows?: number;
};

export function ThemeProfile({ book, maxRows }: ThemeProfileProps) {
  const scores = selectThemeScoresForDisplay(scoreThemeProfile(book), maxRows);
  const hasSignal = scores.some((item) => item.score > 0);

  return (
    <div className="mt-6">
      <h3 className="text-sm font-semibold text-slate-900">Theme Profile</h3>
      {!hasSignal ? (
        <p className="mt-2 text-sm text-slate-500">
          Not enough signal for a theme profile.
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {scores.map((item) => (
            <ThemeScoreRow key={item.id} item={item} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ThemeScoreRow({ item }: { item: ThemeScore }) {
  return (
    <li className="grid grid-cols-[minmax(0,7.5rem)_minmax(0,1fr)_2.5rem] items-center gap-2 sm:grid-cols-[minmax(0,9.5rem)_minmax(0,1fr)_2.75rem]">
      <span className="truncate text-xs font-medium text-slate-600" title={item.label}>
        {item.label}
      </span>
      <div
        className="h-2 overflow-hidden rounded-full bg-slate-100 ring-1 ring-slate-200/80"
        role="meter"
        aria-label={`${item.label} ${item.score}%`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={item.score}
      >
        <div
          className="h-full rounded-full bg-teal-600 transition-[width]"
          style={{ width: `${item.score}%` }}
        />
      </div>
      <span className="text-right text-xs font-medium tabular-nums text-slate-500">
        {item.score}%
      </span>
    </li>
  );
}
