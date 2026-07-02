import { createClient } from "@supabase/supabase-js";

import { getSupabasePublicConfig } from "./env";

export function createSupabaseClient() {
  const { url, anonKey } = getSupabasePublicConfig();
  return createClient(url, anonKey);
}
