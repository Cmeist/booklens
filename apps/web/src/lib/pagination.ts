export const RESULTS_PAGE_SIZE = 25;

export type PaginatedResult<T> = {
  pageItems: T[];
  totalPages: number;
  page: number;
  startIndex: number;
  endIndex: number;
};

export function getTotalPages(count: number, pageSize: number): number {
  if (count <= 0 || pageSize <= 0) {
    return 1;
  }
  return Math.max(1, Math.ceil(count / pageSize));
}

export function paginateItems<T>(
  items: T[],
  page: number,
  pageSize: number = RESULTS_PAGE_SIZE,
): PaginatedResult<T> {
  const totalPages = getTotalPages(items.length, pageSize);
  const clampedPage = Math.min(Math.max(1, page), totalPages);
  const startIndex = items.length === 0 ? 0 : (clampedPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, items.length);

  return {
    pageItems: items.slice(startIndex, endIndex),
    totalPages,
    page: clampedPage,
    startIndex,
    endIndex,
  };
}
