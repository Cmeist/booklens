import { pageShellClassName } from "@/lib/ui";

export default function Loading() {
  return (
    <div className={`flex ${pageShellClassName} items-center justify-center px-4 py-16`}>
      <div className="rounded-2xl border border-slate-200 bg-white px-8 py-6 text-center shadow-sm">
        <p className="text-sm font-medium text-slate-900">Loading BookLens data...</p>
        <p className="mt-1 text-sm text-slate-600">
          Fetching books from Supabase or the local sample fixture.
        </p>
      </div>
    </div>
  );
}
