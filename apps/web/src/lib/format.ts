export function formatYear(year: number | null, decade: string | null): string {
  if (year !== null) {
    return String(year);
  }
  if (decade) {
    return decade;
  }
  return "Unknown year";
}

export function formatPageCount(pageCount: number | null): string {
  if (pageCount === null) {
    return "Unknown length";
  }
  return `${pageCount.toLocaleString()} pages`;
}

export function formatRating(averageRating: number | null): string {
  if (averageRating === null) {
    return "No rating";
  }
  return averageRating.toFixed(2);
}

export function formatRatingCount(ratingCount: number | null): string {
  if (ratingCount === null) {
    return "No ratings";
  }
  if (ratingCount >= 1_000_000) {
    return `${(ratingCount / 1_000_000).toFixed(1)}M ratings`;
  }
  if (ratingCount >= 1_000) {
    return `${(ratingCount / 1_000).toFixed(0)}K ratings`;
  }
  return `${ratingCount.toLocaleString()} ratings`;
}

export function formatScore(score: number): string {
  return `${Math.round(score * 100)}% match`;
}
