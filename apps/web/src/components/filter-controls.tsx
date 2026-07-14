"use client";

import {
  getActiveFilterChips,
  type ActiveFilterChip,
  type BookFilters,
} from "@/lib/filters";

const MIN_RATING_OPTIONS = [
  { value: "", label: "Any rating" },
  { value: "3.5", label: "3.5+" },
  { value: "4.0", label: "4.0+" },
  { value: "4.2", label: "4.2+" },
];

const MIN_RATING_COUNT_OPTIONS = [
  { value: "", label: "Any popularity" },
  { value: "1000", label: "1K+ ratings" },
  { value: "100000", label: "100K+ ratings" },
  { value: "1000000", label: "1M+ ratings" },
];

const PAGE_COUNT_PRESETS = [
  { value: "", label: "Any length" },
  { value: "0-249", label: "Short (under 250)" },
  { value: "250-450", label: "Medium (250–450)" },
  { value: "451-9999", label: "Long (451+)" },
];

function parsePageCountPreset(value: string): Pick<BookFilters, "minPageCount" | "maxPageCount"> {
  if (!value) {
    return { minPageCount: null, maxPageCount: null };
  }

  const [minRaw, maxRaw] = value.split("-");
  return {
    minPageCount: minRaw ? Number(minRaw) : null,
    maxPageCount: maxRaw ? Number(maxRaw) : null,
  };
}

function pageCountPresetValue(filters: BookFilters): string {
  if (filters.minPageCount === null && filters.maxPageCount === null) {
    return "";
  }
  if (filters.minPageCount === 0 && filters.maxPageCount === 300) {
    return "0-300";
  }
  if (filters.minPageCount === 250 && filters.maxPageCount === 400) {
    return "250-400";
  }
  if (filters.minPageCount === 400 && filters.maxPageCount === 9999) {
    return "400-9999";
  }
  return "custom";
}

export function FilterControls({
  filters,
  decadeOptions,
  onChange,
}: {
  filters: BookFilters;
  decadeOptions: string[];
  onChange: (next: BookFilters) => void;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1.4fr_repeat(3,minmax(0,1fr))]">
      <label className="block sm:col-span-2 lg:col-span-1">
        <span className="sr-only">Search books</span>
        <input
          type="search"
          value={filters.searchQuery}
          onChange={(event) => onChange({ ...filters, searchQuery: event.target.value })}
          placeholder="Search title, author, description, or tags"
          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm outline-none ring-teal-500 placeholder:text-slate-400 focus:ring-2"
        />
      </label>

      <label className="block">
        <span className="sr-only">Filter by decade</span>
        <select
          value={filters.decade ?? ""}
          onChange={(event) =>
            onChange({ ...filters, decade: event.target.value || null })
          }
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="">All decades</option>
          {decadeOptions.map((decade) => (
            <option key={decade} value={decade}>
              {decade}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="sr-only">Minimum average rating</span>
        <select
          value={filters.minAverageRating?.toString() ?? ""}
          onChange={(event) =>
            onChange({
              ...filters,
              minAverageRating: event.target.value ? Number(event.target.value) : null,
            })
          }
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm outline-none focus:ring-2 focus:ring-teal-500"
        >
          {MIN_RATING_OPTIONS.map((option) => (
            <option key={option.label} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="sr-only">Page count range</span>
        <select
          value={pageCountPresetValue(filters)}
          onChange={(event) => {
            if (event.target.value === "custom") {
              return;
            }
            onChange({ ...filters, ...parsePageCountPreset(event.target.value) });
          }}
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm outline-none focus:ring-2 focus:ring-teal-500"
        >
          {PAGE_COUNT_PRESETS.map((option) => (
            <option key={option.label} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label className="block sm:col-span-2 lg:col-span-1">
        <span className="sr-only">Minimum rating count</span>
        <select
          value={filters.minRatingCount?.toString() ?? ""}
          onChange={(event) =>
            onChange({
              ...filters,
              minRatingCount: event.target.value ? Number(event.target.value) : null,
            })
          }
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm outline-none focus:ring-2 focus:ring-teal-500"
        >
          {MIN_RATING_COUNT_OPTIONS.map((option) => (
            <option key={option.label} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

export function ActiveFilterChips({
  filters,
  onClearChip,
  onClearAll,
}: {
  filters: BookFilters;
  onClearChip: (chip: ActiveFilterChip) => void;
  onClearAll: () => void;
}) {
  const chips = getActiveFilterChips(filters);
  if (chips.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
        Active filters
      </span>
      {chips.map((chip) => (
        <button
          key={`${chip.key}-${chip.label}`}
          type="button"
          onClick={() => onClearChip(chip)}
          className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
        >
          {chip.label}
          <span aria-hidden="true" className="text-slate-400">
            ×
          </span>
          <span className="sr-only">Remove filter</span>
        </button>
      ))}
      <button
        type="button"
        onClick={onClearAll}
        className="text-xs font-medium text-teal-700 hover:text-teal-800"
      >
        Clear all
      </button>
    </div>
  );
}

export type { ActiveFilterChip };
