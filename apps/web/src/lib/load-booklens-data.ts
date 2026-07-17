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

const PAGE_SIZE = 500;
const TOP_TAGS_LIMIT = 100;

type SupabaseClient = ReturnType<typeof createSupabaseClient>;

async function fetchAllBooks(supabase: SupabaseClient): Promise<BooksWithTagsRow[]> {
  const rows: BooksWithTagsRow[] = [];
  let from = 0;

  while (true) {
    const to = from + PAGE_SIZE - 1;
    const { data, error } = await supabase
      .from("books_with_tags")
      .select("*")
      .order("title", { ascending: true })
      .order("id", { ascending: true })
      .range(from, to);

    if (error) {
      throw new Error(`Failed to load books from Supabase: ${error.message}`);
    }

    const page = (data ?? []) as BooksWithTagsRow[];
    rows.push(...page);

    if (page.length < PAGE_SIZE) {
      break;
    }

    from += PAGE_SIZE;
  }

  return rows;
}

async function fetchAllRecommendations(
  supabase: SupabaseClient,
): Promise<BookRecommendationsRow[]> {
  const rows: BookRecommendationsRow[] = [];
  let from = 0;

  while (true) {
    const to = from + PAGE_SIZE - 1;
    const { data, error } = await supabase
      .from("book_recommendations")
      .select("*")
      .order("book_id", { ascending: true })
      .order("score", { ascending: false })
      .order("similar_book_id", { ascending: true })
      .range(from, to);

    if (error) {
      throw new Error(`Failed to load recommendations from Supabase: ${error.message}`);
    }

    const page = (data ?? []) as BookRecommendationsRow[];
    rows.push(...page);

    if (page.length < PAGE_SIZE) {
      break;
    }

    from += PAGE_SIZE;
  }

  return rows;
}

async function fetchTopTags(supabase: SupabaseClient): Promise<TopTagsRow[]> {
  const { data, error } = await supabase
    .from("top_tags")
    .select("*")
    .order("book_count", { ascending: false })
    .order("tag", { ascending: true })
    .limit(TOP_TAGS_LIMIT);

  if (error) {
    throw new Error(`Failed to load top tags from Supabase: ${error.message}`);
  }

  return (data ?? []) as TopTagsRow[];
}

async function fetchSupabaseData(): Promise<BookLensData> {
  const supabase = createSupabaseClient();

  const [bookRows, topTagRows, recommendationRows] = await Promise.all([
    fetchAllBooks(supabase),
    fetchTopTags(supabase),
    fetchAllRecommendations(supabase),
  ]);

  return {
    source: "supabase",
    books: bookRows.map(mapBookRow),
    topTags: sortTopTags(topTagRows.map(mapTopTagRow)),
    recommendations: sortRecommendations(recommendationRows.map(mapRecommendationRow)),
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
