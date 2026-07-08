import { BookExplorer } from "@/components/book-explorer";
import { EmptyBooksState } from "@/components/empty-books-state";
import { loadBookLensData } from "@/lib/load-booklens-data";

export const revalidate = 300;

export default async function ExplorePage() {
  const { data, warning } = await loadBookLensData();

  if (data.books.length === 0) {
    return <EmptyBooksState source={data.source} />;
  }

  return <BookExplorer data={data} loadWarning={warning} />;
}
