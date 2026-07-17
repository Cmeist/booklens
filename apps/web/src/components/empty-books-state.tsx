import type { BookLensDataSource } from "@/lib/booklens-data";
import { pageShellClassName } from "@/lib/ui";

type EmptyBooksStateProps = {
  source: BookLensDataSource;
};

export function EmptyBooksState({ source }: EmptyBooksStateProps) {
  return (
    <div className={`flex ${pageShellClassName} items-center justify-center px-4 py-16`}>
      <div className="reading-room-card max-w-lg rounded-2xl p-8 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-walnut">
          The reading room is quiet
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">No books available</h1>
        <p className="mt-3 text-sm text-ink-soft">
          {source === "supabase"
            ? "Supabase is connected, but the database has no book records yet. Run migrations and seed the project, or use the committed sample fixture locally without Supabase env vars."
            : "The committed sample fixture is empty. Run make pipeline-demo to regenerate local data."}
        </p>
      </div>
    </div>
  );
}
