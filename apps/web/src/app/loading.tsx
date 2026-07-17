import { pageShellClassName } from "@/lib/ui";

export default function Loading() {
  return (
    <div className={`flex ${pageShellClassName} items-center justify-center px-4 py-16`}>
      <div className="reading-room-card rounded-2xl px-8 py-6 text-center">
        <p className="font-display text-xl font-semibold text-ink">Opening the reading room…</p>
        <p className="mt-1 text-sm text-ink-soft">
          Fetching books from Supabase or the local sample fixture.
        </p>
      </div>
    </div>
  );
}
