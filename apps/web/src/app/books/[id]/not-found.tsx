import Link from "next/link";

export default function BookNotFound() {
  return (
    <div className="flex min-h-full items-center justify-center bg-[#f4f1ea] px-4 py-16">
      <div className="max-w-lg rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
          BookLens
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Book not found</h1>
        <p className="mt-3 text-sm text-slate-600">
          That book id is not in the current dataset. Return to the explorer to browse available
          books.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex rounded-full bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800"
        >
          Back to explorer
        </Link>
      </div>
    </div>
  );
}
