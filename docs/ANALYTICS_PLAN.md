# BookLens Analytics Page Plan

Agent-ready redesign plan for `/analytics`. This document is the authority for the analytics UX redesign. Implement only what this file specifies.

Do **not** edit `docs/PLAN.md` or `docs/DESIGN.md` during implementation. Their Phase 8 / §4.6 chart inventories are historical context only.

## Objective

Refocus `/analytics` from a generic chart inventory into concise proof of catalog quality and recommendation behavior:

1. **Data coverage** — compact rating, page-count, publication-year, and cover coverage.
2. **Catalog shape** — publication decades plus one useful correlation view (`ratingCount` vs `averageRating`).
3. **Discovery signals** — recommendation-reason frequency and a short hidden-gems list.

Hard visual budget (v1):

| Slot | Content |
|------|---------|
| Panel 1 | One four-metric coverage `<dl>` |
| Panel 2 | Publication-decade bar list |
| Panel 3 | Rating-count vs average-rating scatter |
| Panel 4 | One discovery card: recommendation coverage + reason-frequency bars + hidden gems (not separate bordered cards per item) |

Page header and section headings do **not** count as panels. No other v1 widgets.

**Panel border rule:** count only the four visual panels. Strip the current outer `analytics-section` wrapper that wraps the whole page content in one big bordered card (`rounded-2xl border …`). Section wrappers may use spacing only; do not add a fifth bordered chart container.

Structure:

- One page `<h1>` (“Analytics”)
- Exactly three titled sections (`<h2>`)
- At most four bordered visual panels
- Panel titles use `<h3>`
- Bounded lists, honest sparse-data states
- No chart-library dependency

## Scope

### In scope (implementation may edit)

- `apps/web/src/lib/analytics.ts`
- `apps/web/src/app/analytics/page.tsx`
- `apps/web/src/components/analytics-section.tsx`
- Optional: one focused pure-function test file under `apps/web/` **only if** a test runner decision is made and reported (see Validation)

### Out of scope (must not change)

- `docs/PLAN.md`, `docs/DESIGN.md`
- `apps/web/src/lib/load-booklens-data.ts` (reuse as-is; pass already-loaded `recommendations`)
- Home behavior / `home-summary.ts` logic (reuse only exported `formatCoverageLabel`)
- Schema migrations, auth, client writes
- Chart libraries or new production dependencies
- Nav / Home redesign, Explorer changes, deployment
- Unrelated refactors

### Preserve

- Fixture fallback via `loadBookLensData()`
- ISR: `export const revalidate = 300`
- Server Components only (no `"use client"` on analytics page/section)
- Read-only Supabase access pattern
- Current routes
- Unrelated dirty working-tree files

## Documentation authority

| Doc | Role after this plan |
|-----|----------------------|
| `docs/ANALYTICS_PLAN.md` (this file) | Governs analytics redesign |
| `docs/PLAN.md` Phase 8 | Historical; old chart inventory |
| `docs/DESIGN.md` §4.6 / Hidden Gems note | Historical; this plan elevates bounded hidden gems into analytics v1 |

## Current-state evidence (verified against source)

### Files

| Path | Role today |
|------|------------|
| `apps/web/AGENTS.md` | Next.js version differs from training data; read `apps/web/node_modules/next/dist/docs/` before code edits |
| `apps/web/src/app/analytics/page.tsx` | Loads data; passes `books` + `topTags`; **does not pass** `recommendations`; single `<h1>` already present |
| `apps/web/src/components/analytics-section.tsx` | Duplicate inner “Analytics” `<h2>`; KPI `SummaryCard`s; top tags; decades; tag ratings; page scatter; rating scatter + point `<ul>` |
| `apps/web/src/lib/analytics.ts` | `buildAnalyticsSnapshot(books, topTags)`; decades; tag averages; both scatters; no recommendation helpers; no coverage strip; no scatter cap |
| `apps/web/src/lib/load-booklens-data.ts` | Already fetches `book_recommendations` into `data.recommendations`; fixture fallback on missing config / fetch error |
| `apps/web/src/lib/home-summary.ts` | Exports `formatCoverageLabel(percent, known, total)`; `coveragePercent` is **private** — do not import it; do not change Home |
| `apps/web/src/lib/booklens-data.ts` | `BookLensData` includes `recommendations`; `MAX_RECOMMENDATIONS = 5` is for detail UI only, not analytics |
| `apps/web/src/lib/types.ts` | `BookRecommendation`: `{ bookId, similarBookId, score, reasons: string[] }` — **array**, not a single `reason` string |

### Facts the implementer must not rediscover incorrectly

1. `loadBookLensData()` already returns recommendations. Wire them through; do **not** add a second query or loader.
2. `buildAnalyticsSnapshot()` still accepts `topTags`. Remove `topTags` from component and snapshot signatures after removing the top-tags panel.
3. No frontend test runner exists (`apps/web/package.json` scripts: `dev`, `build`, `start`, `lint` only).
4. App code has no `.limit()` / `.range()` on Supabase selects. PostgREST default `max_rows` (often 1000) can still truncate silently. Full-catalog correctness is required (see Stop conditions).
5. `Book` already has `publicationYear` and `coverUrl`; current analytics ignores them. Coverage uses those fields; decade chart continues to use `decade`.

### Removals (must delete from UI / unused snapshot fields)

- KPI summary cards (`SummaryCard` grid: books, avg rating, avg page count, rated books)
- Raw top-tags chart
- Average-rating-by-tag chart (`TagRatingList`, `buildAverageRatingByTag` once unused)
- Page-count vs rating scatter
- Duplicate inner “Analytics” heading inside the section wrapper
- Scatter point `<ul>` lists under SVG plots

## Exact data rules

### Coverage (Panel 1)

Add pure coverage metrics in `analytics.ts`. Reuse only exported `formatCoverageLabel()` from `home-summary.ts`. Do not modify Home behavior. Inline percent math locally (same idea as private `coveragePercent`: `total <= 0 ? 0 : Math.round((known / total) * 100)`).

| Metric | Numerator | Denominator |
|--------|-----------|-------------|
| Rating | `averageRating !== null` | `books.length` |
| Page count | `pageCount !== null` | `books.length` |
| Publication year | `publicationYear !== null` (do **not** substitute `decade`) | `books.length` |
| Cover | `coverUrl !== null && coverUrl.trim() !== ""` | `books.length` |

Each rendered value must show percent and raw fraction via `formatCoverageLabel`. Empty catalog remains handled by page-level `EmptyBooksState` (section not rendered).

Remove standalone average-rating and average-page-count KPI cards. If a mean appears in explanatory copy, label it “mean of book averages” with rated-book denominator; never imply rating-count weighting. Prefer omitting means entirely in v1.

### Valid recommendations

A **valid** recommendation has:

- `bookId` present in the loaded `books` id set
- `similarBookId` present in the same set
- `bookId !== similarBookId`

#### Recommendation coverage

- Numerator: count of distinct `bookId` values among valid recommendations
- Denominator: `books.length`
- Display with `formatCoverageLabel` (or identical fraction formatting)

#### Reason frequency

Source field: `BookRecommendation.reasons: string[]`.

For each valid recommendation row:

1. Map each `reasons` entry through `trim()`.
2. Drop empty strings.
3. Deduplicate within that row (same label counts once per row).
4. Increment the global count for each remaining label by 1.

Sort: count descending, then reason ascending (`localeCompare`). Show at most **six**.

Sparse gate: if no valid reason entries exist after filtering, show: `No recommendation reasons available in the current dataset.` Do not fabricate or fuzzy-merge reasons.

### Hidden gems

Eligibility (all required):

- `averageRating !== null`
- `ratingCount !== null`
- `ratingCount >= 3`

Popularity gate:

1. Collect eligible books’ `ratingCount` values.
2. Median of those counts (0-indexed sort ascending):
   - odd `n`: value at index `Math.floor(n / 2)`
   - even `n`: arithmetic mean of values at `n/2 - 1` and `n/2`
3. Keep books with `ratingCount <= median`.

Quality gate: `averageRating >= 4.0`.

Stable ranking (apply after gates):

1. `averageRating` descending
2. `ratingCount` ascending
3. `title` ascending (`localeCompare`)
4. `id` ascending (`localeCompare`)

Show at most **five** books, each linked to `/books/{id}` (same `Link` pattern as `home-dashboard.tsx` / Explorer). Each row: title (link) plus compact meta `averageRating` (2 decimals) and `ratingCount` (e.g. `4.35 · 12 ratings`). No cover thumbnails in v1.

Label honestly as “high average rating with lower rating count,” not a statistically adjusted popularity score.

No eligible books after gates → `No hidden gems match the current thresholds.`

### Scatter (Panel 3)

Keep:

- `MIN_POINTS_FOR_SCATTER = 2` (gate: fewer than 2 eligible points → `Need at least two books with both rating count and average rating to plot this chart.`)
- `normalizeScatterX` / `normalizeScatterY`
- Only rating-count vs average-rating points (require non-null `averageRating` and non-null `ratingCount`)

Add:

- Deterministic sort before plot: `ratingCount` descending, `title` ascending, `id` ascending
- Cap at **40** points after sort
- If capped, show copy: `Showing 40 of N books.` (N = uncapped eligible count)
- Remove the duplicate point `<ul>`
- Retain each SVG point `<title>`; add SVG `aria-label` naming both axes (e.g. rating count and average rating)
- Drop current scatter `min-w-[280px]` (or equivalent) so the plot does not force horizontal overflow at 320px; keep the SVG fluid (`w-full`)

### Decades (Panel 2)

Keep `buildDecadeDistribution()` and the current gate: show chart only when at least one decade label is not `"Unknown decade"`.

Unavailable copy when the gate fails: `Not enough publication decade metadata to chart a meaningful distribution.`

Unknown values must not make the chart appear meaningful.

## Target UX

### Page (`analytics/page.tsx`)

- Keep `revalidate = 300`, warning banner, `EmptyBooksState` when `books.length === 0`
- Keep single page `<h1>` Analytics
- Update supporting sentence to match new product direction (coverage + catalog shape + discovery)
- Pass: `books={data.books}`, `recommendations={data.recommendations}`, `source={data.source}`
- Do **not** pass `topTags`

### Section (`analytics-section.tsx`)

Exactly three `<h2>` sections:

1. **Data coverage** — Panel 1 (`<dl>` four metrics)
2. **Catalog shape** — Panel 2 (decades) + Panel 3 (scatter)
3. **Discovery signals** — Panel 4 (single bordered card containing: recommendation coverage line, reason-frequency `BarList` or equivalent, hidden-gems list)

Remove outer duplicate “Analytics” heading. A compact data-source badge (`bookCount` + Supabase/fixture label) may remain near the top without counting as a panel if it is not a bordered chart widget; prefer placing it in the page header area or as non-panel metadata beside section 1.

Reuse existing CSS bar-list / unavailable / badge patterns from the current file. No new chart library.

Accessibility / responsive requirements:

- One `<h1>`, section `<h2>`, panel `<h3>`
- Text values alongside visual bars
- Visible sparse states
- Labeled SVG
- No client component
- No horizontal overflow at 320px width

## Ordered implementation phases

### Phase 0 — Preflight

1. `git status --short` — note unrelated dirty files; do not revert them.
2. Read:
   - `apps/web/AGENTS.md`
   - `apps/web/src/app/analytics/page.tsx`
   - `apps/web/src/components/analytics-section.tsx`
   - `apps/web/src/lib/analytics.ts`
   - `apps/web/src/lib/load-booklens-data.ts`
   - `apps/web/src/lib/home-summary.ts` (confirm exported `formatCoverageLabel`; do not change Home helpers)
   - `apps/web/src/lib/types.ts` (`BookRecommendation.reasons`)
   - Relevant Next.js docs under `apps/web/node_modules/next/dist/docs/` if App Router APIs are unclear
3. Verify recommendation shape and fixture fallback path.
4. Check whether Supabase results look complete vs row-limited (row counts vs expected catalog size). If truncation is confirmed or strongly suspected, **stop** — see Stop conditions.

### Phase 1 — Pure helpers (`analytics.ts`)

1. Add coverage builder (four numerators + percents).
2. Add `filterValidRecommendations(books, recommendations)`.
3. Add recommendation coverage + reason-frequency helpers (bounds above).
4. Add hidden-gems helper (median + ranking + cap 5).
5. Bound rating-count scatter: sort + cap 40; expose uncapped count for “Showing 40 of N”.
6. Simplify `AnalyticsSnapshot` to fields the UI needs; delete unused tag-rating / page-scatter / top-tag snapshot outputs once UI no longer imports them.
7. Change signature to accept `recommendations` instead of `topTags` (or drop unused args). Keep pure / side-effect free.

### Phase 2 — Route wiring (`analytics/page.tsx`)

1. Pass `data.recommendations` into `AnalyticsSection`.
2. Stop passing `topTags`.
3. Keep `revalidate`, warning banner, `EmptyBooksState`, single `<h1>`.

### Phase 3 — UI (`analytics-section.tsx`)

1. Render exactly three labeled sections and four panels per Hard visual budget.
2. Remove `SummaryCard`, `TagRatingList`, duplicate “Analytics” heading, top tags, tag ratings, page scatter, scatter point lists.
3. Wire coverage `<dl>`, decade bars, scatter, discovery card.
4. Link hidden gems to `/books/{id}`.

### Phase 4 — Accessibility / responsiveness

1. Heading hierarchy as specified.
2. Sparse states visible.
3. SVG `aria-label` + point `<title>`.
4. Smoke-check 320px: no horizontal overflow from panels.

### Phase 5 — Validation

1. `cd apps/web && npm run lint`
2. `cd apps/web && npm run build`
3. Manual checks (below).
4. Tests: either add a **dev-only** runner + script as an explicitly reported decision, or document why tests were skipped and complete the manual cases. Do **not** install a test runner silently.

## Implementation tests (recommended)

One focused pure-function test file covering:

- Coverage denominators / numerators (including empty cover trim)
- Recommendation validity + reason ordering / within-row dedupe / cap 6
- Hidden-gem median (odd and even), quality gate, ranking, cap 5
- Scatter sort + cap 40 + gate at `< 2` points

If no runner is added, list these as manual reasoning checks against fixture data in the handoff.

## Feature suggestions (ranked; not auto-scope)

| Tier | Ideas |
|------|--------|
| Recommended now (in this redesign) | Coverage strip; recommendation-reason breakdown; recommendation coverage; hidden gems |
| Good follow-ups | Analytics → Explorer deep links; publication-year histogram; author/source concentration; catalog theme profile; local-profile comparison |
| Scale-only | Bounded SQL/RPC analytics summaries or snapshot table (when in-memory load truncates) |
| Defer | NYT/ingestion dashboards; time series; chart library; ML clustering |

Do not implement follow-ups / scale / defer items unless this plan is amended.

## Acceptance criteria

- [ ] One page `<h1>`, exactly three titled analytics sections, ≤ four bordered visual panels
- [ ] Recommendations passed from existing `loadBookLensData()` result; no duplicate fetch
- [ ] Coverage shows four percentages with numerators and denominators
- [ ] Only decade + rating-count scatter remain from current charts
- [ ] Scatter renders ≤ 40 points and no point list; capped copy when needed
- [ ] Discovery card shows recommendation coverage, ≤ 6 reasons, ≤ 5 hidden gems, honest empty states
- [ ] No production dependency or chart library added
- [ ] No schema, auth, nav, Home, deployment, or unrelated changes
- [ ] `cd apps/web && npm run lint` passes
- [ ] `cd apps/web && npm run build` passes

## Manual checks

1. **Fixture path**: unset / missing Supabase env → sample fixture renders; warning absent (config missing) or present (fetch error) per existing loader rules.
2. **Supabase path** (when credentials exist): analytics renders live data; compare book/recommendation counts to expected catalog; flag truncation.
3. **Sparse states**: force or find datasets lacking decades / scatter points / reasons / gems → unavailable copy, not empty misleading charts.
4. **Deterministic ordering**: reasons, gems, scatter order stable across reloads.
5. **Panel budget**: count bordered visual panels ≤ 4.
6. **Desktop + 320px**: layout readable; no horizontal overflow.

## Stop conditions

Stop and ask the project owner before continuing if:

- Supabase `books_with_tags` or `book_recommendations` results are truncated / incomplete for full-catalog metrics
- Required symbols/paths above are missing or renamed
- Meeting acceptance criteria seems to require a chart library, schema change, or second data loader
- Unrelated dirty files would need editing to finish

On truncation: do **not** silently publish partial metrics. Replace the approach with a bounded SQL/RPC or snapshot plan (out of this v1 scope unless owner expands scope).

## Expected final handoff

Report:

1. Files changed
2. Commands run + results (`lint`, `build`)
3. Manual checks performed
4. Whether tests were added or skipped (and why)
5. Assumptions made
6. Any scale / truncation concern
7. Deliberate non-actions (e.g. left `PLAN.md` / `DESIGN.md` untouched)
)
