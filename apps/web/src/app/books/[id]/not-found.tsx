import Link from "next/link";

import { buttonPrimaryClassName, pageShellClassName } from "@/lib/ui";

export default function BookNotFound() {
  return (
    <div className={`flex ${pageShellClassName} items-center justify-center px-4 py-16`}>
      <div className="reading-room-card max-w-lg rounded-2xl p-8 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-walnut">
          Missing from the shelves
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Book not found</h1>
        <p className="mt-3 text-sm text-ink-soft">
          That book id is not in the current dataset. Return to the explorer to browse available
          books.
        </p>
        <Link href="/explore" className={`mt-6 ${buttonPrimaryClassName}`}>
          Back to Discover
        </Link>
      </div>
    </div>
  );
}
