import type { BookLensDataSource } from "@/lib/booklens-data";
import { pageShellClassName } from "@/lib/ui";

type EmptyBooksStateProps = {
  source: BookLensDataSource;
};

export function EmptyBooksState({ source }: EmptyBooksStateProps) {
  return (
    <div className={`flex ${pageShellClassName} items-center justify-center px-4 py-16`}>
      <div className="max-w-lg rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
          BookLens
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">No books available</h1>
        <p className="mt-3 text-sm text-slate-600">
          {source === "supabase"
            ? "Supabase is connected, but the database has no book records yet. Run migrations and seed the project, or use the committed sample fixture locally without Supabase env vars."
            : "The committed sample fixture is empty. Run make pipeline-demo to regenerate local data."}
        </p>
      </div>
    </div>
  );
}
