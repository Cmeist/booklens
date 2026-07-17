"use client";

import { useState } from "react";

import {
  DETAIL_TAGS_MAX,
  filterDisplayTags,
  PREVIEW_TAGS_MAX,
} from "@/lib/display-tags";

const tagPillClassName =
  "rounded-full bg-paper-deep px-2.5 py-0.5 text-xs font-medium text-ink-soft";

const overflowPillClassName =
  "rounded-full bg-paper-raised px-2.5 py-0.5 text-xs font-medium text-ink-faint ring-1 ring-rule";

const toggleButtonClassName =
  "rounded-full bg-paper-raised px-2.5 py-0.5 text-xs font-medium text-ink-soft ring-1 ring-rule transition-colors hover:bg-paper-deep";

type BookTagsProps = {
  tags: string[];
  /** preview: cap + static "+N more"; page: cap + Show more/fewer */
  mode: "preview" | "page";
};

export function BookTags({ tags, mode }: BookTagsProps) {
  const filtered = filterDisplayTags(tags);

  if (filtered.length === 0) {
    return null;
  }

  if (mode === "preview") {
    const overflow = Math.max(0, filtered.length - PREVIEW_TAGS_MAX);
    const visible =
      overflow > 0 ? filtered.slice(0, PREVIEW_TAGS_MAX) : filtered;
    return (
      <div className="mt-3 flex flex-wrap gap-1.5">
        {visible.map((tag) => (
          <span key={tag} className={tagPillClassName}>
            {tag}
          </span>
        ))}
        {overflow > 0 ? (
          <span className={overflowPillClassName}>+{overflow} more</span>
        ) : null}
      </div>
    );
  }

  return <ExpandableBookTags tags={filtered} />;
}

function ExpandableBookTags({ tags }: { tags: string[] }) {
  const [expanded, setExpanded] = useState(false);
  const needsToggle = tags.length > DETAIL_TAGS_MAX;
  const visible = expanded || !needsToggle ? tags : tags.slice(0, DETAIL_TAGS_MAX);
  const hiddenCount = tags.length - DETAIL_TAGS_MAX;

  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {visible.map((tag) => (
        <span key={tag} className={tagPillClassName}>
          {tag}
        </span>
      ))}
      {needsToggle ? (
        <button
          type="button"
          onClick={() => setExpanded((current) => !current)}
          className={toggleButtonClassName}
        >
          {expanded ? "Show fewer" : `Show more (+${hiddenCount})`}
        </button>
      ) : null}
    </div>
  );
}
