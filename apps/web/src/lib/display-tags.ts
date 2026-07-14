import type { TopTag } from "./types";

/** Tags longer than this are treated as noisy catalog junk. */
export const MAX_DISPLAY_TAG_LENGTH = 40;

export const TOP_TAGS_COLLAPSED_COUNT = 10;
export const TOP_TAGS_EXPANDED_COUNT = 40;
export const CARD_TAGS_MAX = 3;
export const PREVIEW_TAGS_MAX = 10;
export const DETAIL_TAGS_MAX = 10;

const NOISE_TAGS = new Set(["fiction", "general", "large type books"]);

export function isDisplayableTag(tag: string): boolean {
  const trimmed = tag.trim();
  if (!trimmed) {
    return false;
  }
  if (trimmed.length > MAX_DISPLAY_TAG_LENGTH) {
    return false;
  }
  const lower = trimmed.toLowerCase();
  if (lower.startsWith("nyt:")) {
    return false;
  }
  if (NOISE_TAGS.has(lower)) {
    return false;
  }
  return true;
}

export function filterDisplayTags(tags: string[]): string[] {
  return tags.filter(isDisplayableTag);
}

export function filterDisplayTopTags(topTags: TopTag[]): TopTag[] {
  return topTags.filter((item) => isDisplayableTag(item.tag));
}

export function truncateTags(
  tags: string[],
  max: number,
): { visible: string[]; overflow: number } {
  const filtered = filterDisplayTags(tags);
  if (filtered.length <= max) {
    return { visible: filtered, overflow: 0 };
  }
  return {
    visible: filtered.slice(0, max),
    overflow: filtered.length - max,
  };
}
