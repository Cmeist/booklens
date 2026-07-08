import Link from "next/link";

import {
  contentContainerClassName,
  linkClassName,
  pageShellClassName,
} from "@/lib/ui";

const scoreRows = ["Overall fit", "Genre overlap", "Pace & length", "Rating alignment"];

export default function CompatibilityPage() {
  return (
    <div className={pageShellClassName}>
      <div className={`${contentContainerClassName} max-w-3xl py-8`}>
        <header className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
            BookLens
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Compatibility
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Profile-aware book scoring — structure ready, scoring engine next.
          </p>
        </header>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <section className="rounded-xl border border-dashed border-slate-300 bg-white/70 p-5">
            <h2 className="text-sm font-semibold text-slate-900">Your profile</h2>
            <p className="mt-1 text-xs text-slate-500">From preferences</p>
            <ul className="mt-4 space-y-2 text-sm text-slate-400">
              <li className="rounded-lg bg-slate-50 px-3 py-2 ring-1 ring-slate-100">
                Favorite genres
              </li>
              <li className="rounded-lg bg-slate-50 px-3 py-2 ring-1 ring-slate-100">
                Preferred length
              </li>
              <li className="rounded-lg bg-slate-50 px-3 py-2 ring-1 ring-slate-100">
                Rating floor
              </li>
            </ul>
            <Link href="/preferences" className={`mt-4 inline-block ${linkClassName}`}>
              Set preferences →
            </Link>
          </section>

          <section className="rounded-xl border border-dashed border-slate-300 bg-white/70 p-5">
            <h2 className="text-sm font-semibold text-slate-900">Match preview</h2>
            <p className="mt-1 text-xs text-slate-500">Select a book in Explore</p>
            <div className="mt-4 rounded-lg bg-slate-50 px-3 py-6 text-center text-sm text-slate-400 ring-1 ring-slate-100">
              No book selected
            </div>
            <ul className="mt-4 space-y-2">
              {scoreRows.map((row) => (
                <li
                  key={row}
                  className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm ring-1 ring-slate-100"
                >
                  <span className="text-slate-500">{row}</span>
                  <span className="font-medium text-slate-300">—</span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <p className="mt-8 text-sm text-slate-500">
          <Link href="/explore" className={linkClassName}>
            Explore books
          </Link>{" "}
          while compatibility scoring is built out.
        </p>
      </div>
    </div>
  );
}
