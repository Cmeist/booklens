import "server-only";

import { loadFixtureData, sortRecommendations, sortTopTags, type BookLensData } from "@/lib/booklens-data";
import { createSupabaseClient } from "@/lib/supabase/client";
import { hasSupabaseConfig } from "@/lib/supabase/env";
import {
  mapBookRow,
  mapRecommendationRow,
  mapTopTagRow,
  type BookRecommendationsRow,
  type BooksWithTagsRow,
  type TopTagsRow,
} from "@/lib/supabase/mappers";

export type LoadBookLensDataResult = {
  data: BookLensData;
  warning?: string;
};

async function fetchSupabaseData(): Promise<BookLensData> {
  const supabase = createSupabaseClient();

  const [booksResult, topTagsResult, recommendationsResult] = await Promise.all([
    supabase.from("books_with_tags").select("*").order("title"),
    supabase
      .from("top_tags")
      .select("*")
      .order("book_count", { ascending: false })
      .order("tag", { ascending: true }),
    supabase
      .from("book_recommendations")
      .select("*")
      .order("book_id", { ascending: true })
      .order("score", { ascending: false }),
  ]);

  if (booksResult.error) {
    throw new Error(`Failed to load books from Supabase: ${booksResult.error.message}`);
  }
  if (topTagsResult.error) {
    throw new Error(`Failed to load top tags from Supabase: ${topTagsResult.error.message}`);
  }
  if (recommendationsResult.error) {
    throw new Error(
      `Failed to load recommendations from Supabase: ${recommendationsResult.error.message}`,
    );
  }

  return {
    source: "supabase",
    books: (booksResult.data as BooksWithTagsRow[]).map(mapBookRow),
    topTags: sortTopTags((topTagsResult.data as TopTagsRow[]).map(mapTopTagRow)),
    recommendations: sortRecommendations(
      (recommendationsResult.data as BookRecommendationsRow[]).map(mapRecommendationRow),
    ),
  };
}

export async function loadBookLensData(): Promise<LoadBookLensDataResult> {
  if (!hasSupabaseConfig()) {
    return { data: loadFixtureData() };
  }

  try {
    return { data: await fetchSupabaseData() };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown error while loading Supabase data.";

    return {
      data: loadFixtureData(),
      warning: `${message} Showing committed sample fixture data instead.`,
    };
  }
}
