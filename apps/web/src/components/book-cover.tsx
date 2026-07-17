import type { Book } from "@/lib/types";

const sizeClasses = {
  sm: "h-18 w-12 text-xs",
  md: "h-24 w-16 text-sm",
  lg: "h-42 w-28 text-lg",
} as const;

export function BookCover({
  book,
  size = "md",
}: {
  book: Book;
  size?: keyof typeof sizeClasses;
}) {
  const className = `${sizeClasses[size]} aspect-[2/3] shrink-0 overflow-hidden rounded-[3px_7px_7px_3px] shadow-[0_8px_18px_rgba(55,39,24,0.16)] ring-1 ring-black/10`;

  if (book.coverUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={book.coverUrl}
        alt={`Cover of ${book.title}`}
        className={`${className} bg-paper-deep object-cover`}
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
      className={`${className} relative flex items-center justify-center bg-forest font-display font-semibold text-paper-raised before:absolute before:inset-y-0 before:left-1 before:w-px before:bg-white/25 after:absolute after:inset-x-3 after:top-3 after:h-px after:bg-walnut-soft/70`}
      aria-hidden="true"
    >
      {initials}
    </div>
  );
}
