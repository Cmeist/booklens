import Link from "next/link";

import {
  contentContainerClassName,
  linkClassName,
  pageShellClassName,
} from "@/lib/ui";

const preferenceFields = [
  { id: "genres", label: "Favorite genres", placeholder: "e.g. science fiction, mystery" },
  { id: "length", label: "Preferred length", placeholder: "Short · medium · long" },
  { id: "rating", label: "Minimum rating", placeholder: "e.g. 3.5" },
  { id: "pace", label: "Reading pace", placeholder: "Fast · moderate · slow" },
] as const;

export default function PreferencesPage() {
  return (
    <div className={pageShellClassName}>
      <div className={`${contentContainerClassName} max-w-2xl py-8`}>
        <header>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
            BookLens
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Preferences
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Reading profile inputs for compatibility scoring — saved locally in a later phase.
          </p>
        </header>

        <form className="mt-8 space-y-5" aria-label="Reading preferences (preview)">
          {preferenceFields.map((field) => (
            <div key={field.id}>
              <label
                htmlFor={field.id}
                className="block text-sm font-medium text-slate-700"
              >
                {field.label}
              </label>
              <input
                id={field.id}
                type="text"
                disabled
                placeholder={field.placeholder}
                className="mt-1.5 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400 placeholder:text-slate-400"
              />
            </div>
          ))}

          <p className="text-xs text-slate-500">Profile persistence coming next.</p>
        </form>

        <p className="mt-8 text-sm text-slate-500">
          Preview how preferences feed scoring on{" "}
          <Link href="/compatibility" className={linkClassName}>
            Compatibility
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
