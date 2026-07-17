# BookLens UI Redesign Plan

Status: Curated Reading Room production implementation complete; lint, production build, and route smoke checks pass; interactive cross-browser screenshot QA remains  
Scope: visual system, navigation, and all current web routes  
Selected production theme: **The Curated Reading Room**

Implementation record (2026-07-16): the production app now uses the selected paper, forest-green,
walnut-brown, and ink palette; Newsreader/Geist typography; code-native bookplate and rule chrome;
responsive navigation and Discover filter disclosure; standardized book covers; and themed Home,
Discover, book detail, For You, My Library, Insights, dialog, loading, empty, and not-found states.
No large artwork or raster site chrome was added. Protected behavior modules were left unchanged by
the redesign. Automated verification is recorded in the implementation handoff; browser-driven
interaction, screenshot, zoom, and screen-reader passes remain the final human QA checkpoint.

## 1. Outcome

Make BookLens feel like a thoughtful book product rather than a generic analytics dashboard.
The redesign should be warm, editorial, cover-led, and calm, while keeping the app's strongest
product idea—explainable recommendations—clear and credible.

The target impression is:

> A modern independent reading room with a very good recommendation engine behind the desk.

This is a UI and information-hierarchy redesign. The selected production direction uses small
code-native chrome and no large background or hero artwork. It must not change recommendation
formulas, data contracts, Supabase behavior, local-profile persistence, or route URLs.

### Non-negotiable preservation contract

This is a presentation-layer project. A cleaner layout must not silently remove, weaken, rename in
code, or alter any current product operation. Existing content may move, collapse behind an
accessible disclosure, or receive a new visual treatment, but it must remain reachable and retain
the same meaning and behavior.

The implementation must preserve:

- All route URLs, route parameters, redirects, `notFound()` behavior, and `revalidate = 300` values.
- Supabase reads, 500-row pagination, sorting, mapping, top-tag limits, fixture fallback, warning
  messages, data-source labels, and empty-catalog handling.
- Every Explorer search field, filter, include/exclude rule, tag search, show-more behavior, active
  chip, individual clear action, clear-all action, selected-book preview, empty state, and 25-item
  pagination operation.
- Every book-detail field and operation: cover/fallback, title, author, description, tags, year,
  page count, community rating, rating count, source, source ID, reading-log controls, personal
  rating, story/theme profile, recommendations, reasons, and links to similar-book detail pages.
- Local profile schema version `1`, storage key `booklens.userProfile.v1`, cross-tab storage-event
  updates, normalization, reload persistence, and all existing malformed-data fallbacks.
- Reading statuses `want`, `reading`, and `read`; add/remove confirmations; half-star personal
  ratings from 0.5–5; clear rating; 280-character notes; status messages; and error handling.
- Profile log filtering, searching, sorting, 10-item pagination, catalog lookup, taste derivation,
  all four preferences, preference saving, and the browser-only privacy message.
- Compatibility query-string selection, invalid-book notice, low-signal state, partial-signal note,
  hide-read behavior, search, all three sort modes, 25-result cap, every score dimension, every
  reason, selected-book breakdown, profile summary, and log controls.
- Analytics calculations, sparse-data fallbacks, links, accessible chart labels, three-section
  structure, and four-panel budget governed by `docs/ANALYTICS_PLAN.md`.
- Dialog focus trapping, initial focus, Escape handling, backdrop dismissal, pending/error states,
  focus restoration, live-region announcements, and keyboard operation.

If a proposed visual simplification conflicts with this contract, preserve the operation and adapt
the visual design. Do not change the underlying operation to make the design easier to implement.

## 2. Current-State Audit

The current UI is functional, consistent, responsive at a basic level, and already has sound
states for missing data. It is a good product skeleton. The main problem is that nearly every
screen uses the same visual recipe: Geist, slate text, teal accents, a warm page background,
white bordered cards, small labels, pills, and light shadows. That makes the experience read as
a competent SaaS dashboard rather than a book-discovery destination.

### What to preserve

- The warm off-white page background.
- Honest handling of sparse metadata and unavailable recommendations.
- Existing keyboard-friendly native form controls and semantic page structure.
- Explainable recommendation reasons and compatibility dimensions.
- The desktop Explorer split view.
- Local-only profile language and the separation between community data and personal data.
- Current routes: `/`, `/explore`, `/books/[id]`, `/compatibility`, `/profile`, `/analytics`.
- The analytics scope and data rules in `docs/ANALYTICS_PLAN.md`.

### Cross-app issues

1. **Book covers are not the main visual material.** Covers are small in Explorer and absent from
   Home's featured list, Compatibility results, Profile log entries, and recommendation-heavy
   areas. The UI therefore loses the most emotionally useful imagery in the product.
2. **Hierarchy is too flat.** Many sections use a 14px semibold heading inside an almost identical
   white card. Important discovery content, internal catalog-health data, filters, and secondary
   metadata often receive similar visual weight.
3. **The typography has no editorial voice.** Geist works well for controls and data, but using it
   for every title makes BookLens feel operational rather than literary.
4. **There is too much visible chrome.** Borders, rings, rounded containers, nested cards, and
   pills appear at almost every level. The result is visually busy even though the palette is calm.
5. **The type scale is compressed.** `text-xs`, `text-[11px]`, and `text-[10px]` are pervasive.
   Metadata is compact, but repeated tiny type makes scanning harder and weakens polish.
6. **Teal carries too many jobs.** It identifies the brand, active navigation, primary actions,
   links, selected rows, scores, chart marks, tags, and focus rings. Those meanings need clearer
   separation.
7. **Mobile navigation is an overflowing horizontal pill row.** It remains usable, but it feels
   like a desktop navigation compressed into a phone rather than an intentional mobile pattern.
8. **Motion and interaction feedback are minimal.** Most feedback is a color change; selection,
   filtering, loading, and panel transitions could feel more deliberate without becoming flashy.

### Route-by-route findings

| Route | Current strength | Main issue | Redesign priority |
| --- | --- | --- | --- |
| Home | Clear entry points and data status | Opens as “Discovery dashboard” and leads with internal catalog health instead of books | Highest |
| Explore | Strong filter coverage and useful desktop preview | Dense control stack; tiny covers; tag include/exclude interaction is cryptic | Highest |
| Book detail | Good content completeness and similar-book explanations | One large white slab; source fields are too prominent; cover/title hero lacks drama | High |
| Compatibility | Transparent scoring and good low-signal state | Clinical percentages and nested boxes; almost no book imagery | High |
| Profile | Capable local log and preferences | Form-heavy, dense, and visually detached from the books being logged | High |
| Analytics | Focused scope and honest coverage | Still inherits the generic white-card system; charts need theme alignment | Medium |
| Navigation | Simple route model and active states | Long label set, horizontal overflow on mobile, no clear primary/secondary grouping | High |

## 3. Reference Direction

The redesign should borrow patterns, not branding or exact layouts.

| Reference | Borrow | Do not copy |
| --- | --- | --- |
| [Hardcover](https://hardcover.app/home) | Clear Find / Track / Discover mental model, prominent search, shelves of cover art | Social-network scope or a dark, app-heavy shell |
| [The StoryGraph](https://www.thestorygraph.com/?lang=en) | Mood, pace, and theme language; personal stats that help choose the next book; honest recommendation context | Dense chip walls or feature sprawl |
| [Penguin Random House literary fiction](https://www.penguinrandomhouse.com/books/literary-fiction/) | Editorial headlines, cover-led collections, varied section rhythm, descriptive curation | Publisher-scale mega-navigation and promotional density |
| [Reedsy Discovery](https://reedsy.com/discovery/blog/discovery-awards-2024) | Short editorial hooks and “why this book” language | Long review excerpts in browsing surfaces |

BookLens's distinct position should be **editorial warmth + analytical clarity**. Covers and prose
create desire; scores and reason labels create trust.

## 4. Theme: The Curated Reading Room

This is the selected production direction after comparison in Section 5. The production version is
locked to the walnut-brown revision and small code-native chrome: no large hero artwork, background
illustration, or cover collage should be introduced without a new explicit design decision.

### Brand attributes

- Warm, not beige-on-beige.
- Intelligent, not academic.
- Editorial, not ornamental.
- Personal, not social-first.
- Data-aware, not dashboard-like.
- Quiet, but not empty.

### Visual concept

Use paper-like neutral surfaces, deep library green, ink-black text, walnut-brown and restrained
brass accents, serif display type, and generous negative space. Let book covers provide most of the
page's saturated color. Use only small code-native bookplate, rule, and wordmark ornaments for site
chrome; do not use a large atmospheric hero illustration. Avoid literal paper textures, bookshelf
graphics, faux leather, page-curl effects, and other bookstore pastiche.

### Proposed palette

These should become semantic CSS variables in `globals.css`; component code should consume
semantic names rather than raw hex values.

| Token | Value | Use |
| --- | --- | --- |
| `--paper` | `#F4F0E7` | App background |
| `--paper-raised` | `#FBF9F4` | Cards and raised sections |
| `--paper-deep` | `#EAE3D7` | Secondary bands and selected neutral states |
| `--ink` | `#211F1B` | Primary text |
| `--ink-muted` | `#6C675E` | Secondary text |
| `--line` | `#D8D0C3` | Dividers and quiet borders |
| `--forest` | `#245447` | Brand, primary action, active state |
| `--forest-deep` | `#183B33` | Hover and high-contrast brand surfaces |
| `--forest-soft` | `#DDE9E2` | Explanations and selected backgrounds |
| `--walnut` | `#754B38` | Ratings, editorial labels, secondary actions, and warm explanation chips |
| `--walnut-soft` | `#EADBD0` | Warm supporting surfaces and chip backgrounds |
| `--clay` | `#B85F45` | Destructive/exclusion states only |
| `--brass` | `#B58A3A` | Sparing chart and editorial highlight accents; not rating semantics |
| `--warning-soft` | `#F7E8C8` | Warnings |

Validate all final text/background pairs for WCAG AA. Values may be adjusted during implementation
to meet contrast; the visual relationship matters more than preserving exact hex values.

### Typography

- Add **Newsreader** as the display serif through `next/font/google` in `app/layout.tsx`.
- Keep **Geist** for navigation, body text, controls, labels, and numeric data.
- Remove Geist Mono unless it has a real UI use.
- Use the serif for the wordmark, page titles, book titles in feature contexts, and editorial
  section headings—not for form controls or dense metadata.
- Raise the practical floor for visible text to 12px. Reserve 11px for very short tertiary labels;
  eliminate 10px text from ordinary reading surfaces.
- Use a clearer scale: 12 metadata, 14 secondary/body-small, 16 body, 20 card title, 28 section
  title, 40–52 desktop hero title.

### Shape, borders, and shadow

- Default panel radius: 16px; book covers: 6–8px; buttons: 10–12px.
- Keep fully rounded pills only for tags, statuses, and compact segmented controls.
- Prefer section spacing and single dividers over putting every group in a bordered card.
- Use one quiet border or one soft shadow, not both by default.
- Reserve stronger shadow for floating filters, dialogs, and sticky detail panels.

### Cover treatment

- Standardize all covers to a `2 / 3` aspect ratio.
- Use cover sizes by context rather than arbitrary width/height pairs.
- Give missing-cover fallbacks an intentional mini-jacket design: muted color families, title
  initials or a short title, and a subtle spine—not a generic teal gradient.
- Use a quiet bottom shadow to make covers feel physical without adding mock 3D perspective.
- Ensure cover images never cause layout shift by reserving their aspect ratio.

### Original imagery and site chrome

For the selected production theme, site chrome must be small and code-native. Use restrained CSS or
repo-native SVG bookplate marks, short walnut rules, and a subtle wordmark ornament. Do not add a
large raster hero, background illustration, cover collage, or other artwork that occupies primary
content space. Generated imagery is deferred unless the user separately approves a specific
empty-state or supporting illustration after the main UI is working.

- Keep book covers as the most colorful and visually dominant imagery.
- Favor tiny geometric/editorial ornaments that remain subordinate to content and book covers.
- Do not imitate a living artist, publisher identity, existing book cover, or reference site's
  proprietary artwork.
- Avoid embedding important text, controls, status, or navigation inside raster images.
- Treat purely decorative artwork as decorative in markup; provide meaningful alt text only when
  an image communicates content.
- If a later approved use requires raster imagery, export responsive WebP or AVIF variants, reserve
  image dimensions, and keep it outside the primary hero content budget.
- Use CSS or repo-native SVG for the approved lines, bookplate mark, wordmark ornament, dividers,
  and simple shapes. Do not generate raster chrome for the selected production direction.
- Validate legibility with the image absent, while loading, at narrow widths, and under increased
  contrast preferences.
- Store any separately approved assets under `apps/web/public/` with descriptive filenames and
  document the prompt and intended placement so future variants remain visually consistent.

### Motion

- 140–180ms for hover, press, and selection transitions.
- 200–240ms for drawers and panel changes.
- Animate opacity/transform only; avoid layout-heavy animations.
- Respect `prefers-reduced-motion` globally.
- Use motion to clarify where content changed, not to decorate static pages.

## 5. Theme Test Sites and Selection Gate

Before changing the real application UI, build isolated test sites so the themes can be compared
with the same content and states. These are visual prototypes, not production implementations.

### Required theme directions

Build at least three distinct directions:

1. **The Curated Reading Room** — warm paper, serif display type, library green, walnut accents,
   quiet editorial rhythm, and restrained small chrome. This is the selected direction.
2. **The Modern Book Journal** — brighter neutral surfaces, larger typography, generous whitespace,
   bolder cover grids, and clay/cobalt editorial accents. It should feel more like a contemporary
   culture magazine than a traditional library.
3. **The Intelligent Archive** — cooler neutrals, precise sans-serif typography, denser comparison
   tools, structured data treatments, and a restrained high-contrast accent. It should emphasize
   BookLens's analytical credibility without returning to generic SaaS styling.

The directions must differ in layout rhythm, typography, color relationships, imagery, and chrome—not
just swap accent colors on the same page.

### Prototype location and isolation

- Keep prototypes outside production components under `prototypes/ui-themes/`, with one directory
  per theme and a shared comparison index.
- Prefer lightweight static HTML/CSS/TypeScript or another isolated setup that can run locally
  without importing production route components.
- Reuse a small, checked-in representative fixture rather than querying Supabase or reading the
  user's local profile.
- Do not add links to prototypes from the production BookLens navigation.
- Do not include prototype routes or assets in the production deployment bundle.
- Add a short README with one command to run the comparison sites and the local URLs to open.

If maintaining a separate static setup would add disproportionate tooling, a development-only
`/theme-lab` route is acceptable, but it must return 404 in production and remain visually/code-wise
isolated from the real route components.

### Required prototype pages

Each theme must render the same three representative screens:

1. **Home / discovery** — hero, primary actions, personalized match, and a cover-led book shelf.
2. **Explore results** — search, active filters, several book results, selected state, and a detail
   preview at desktop width.
3. **Book detail** — cover hero, title/author, reading action, metadata, theme profile, and similar
   books with recommendation reasons.

Also include the following states somewhere in every direction:

- Real cover plus missing-cover fallback.
- Long title and long author name.
- Normal and selected controls.
- Community rating versus personal match score.
- Empty or low-signal recommendation state.
- Generated background/chrome artwork when that theme proposes it, plus a no-art fallback.

Profile, full filter behavior, pagination, Supabase reads, local storage, and real recommendation
logic are explicitly out of scope for these prototypes.

### Comparison controls

The shared comparison index should provide:

- Direct links to every theme and screen.
- Side-by-side screenshots or embedded previews at 390px and 1440px.
- A theme switcher that preserves the current representative screen.
- A way to disable decorative artwork to compare the underlying hierarchy.
- A short design-rationale card for each direction.

### Evaluation scorecard

Score each direction from 1–5 using the same criteria:

| Criterion | Question |
| --- | --- |
| Bookish identity | Does this unmistakably feel like a book product? |
| BookLens distinctiveness | Does it avoid looking like Goodreads, StoryGraph, or generic SaaS? |
| Discovery desire | Do the covers, hierarchy, and copy make the user want to explore? |
| Explanation clarity | Are recommendation reasons easier to understand than raw scores? |
| Information scanning | Can titles, authors, ratings, tags, and actions be parsed quickly? |
| Mobile quality | Does the design feel intentional at 390px rather than merely compressed? |
| Accessibility | Are contrast, type size, focus, and non-color state cues viable? |
| Extensibility | Can the theme support Profile and Insights without becoming monotonous? |
| Performance risk | Can imagery, fonts, and effects meet a reasonable page budget? |

Record the scores, strongest elements, concerns, and preferred direction in
`prototypes/ui-themes/DECISION.md`.

### Approval gate

This gate was required before production and is now complete. The available outcomes were:

1. Approve one theme as shown.
2. Approve one theme with listed changes.
3. Choose a documented hybrid of specific elements from multiple themes.
4. Request another prototype direction.

The plan's theme name, tokens, imagery direction, and component guidance now reflect the selected
outcome. Delete or archive rejected prototypes only after the user says they are no longer needed
for comparison.

Gate result: **The Curated Reading Room selected**, with walnut brown supporting the library green,
the large hero artwork removed, and only small code-native chrome retained. Keep the rejected test
sites available for reference until the user explicitly asks to remove them.

## 6. Experience Principles

1. **Start with a reader's question.** Home should answer “What might I want to read?” before it
   explains dataset health.
2. **Covers create interest; explanations earn trust.** Pair imagery with concise reasons.
3. **Show one level of structure at a time.** Reduce nested panels and progressively disclose
   filters, source details, and score breakdowns.
4. **Personal and community signals must look different.** Use forest for personal match signal,
   walnut for community rating, neutral ink for catalog facts, brass only for sparing chart/highlight
   accents, and clay only for exclusion, destructive actions, or risk.
5. **Desktop density, mobile focus.** Preserve efficient comparison on large screens; on small
   screens present one primary task and one clear next action at a time.
6. **No decorative data.** Every chart, score, badge, and label should help a reader choose,
   understand, or manage a book.

## 7. Information Architecture and Navigation

Keep the URLs but make labels reader-centered:

| URL | Current label | Proposed label |
| --- | --- | --- |
| `/` | Home | Home |
| `/explore` | Explore | Discover |
| `/compatibility` | Compatibility | For You |
| `/profile` | Profile | My Library |
| `/analytics` | Analytics | Insights |

Desktop navigation:

- Serif BookLens wordmark at left.
- Discover, For You, and My Library as primary navigation.
- Insights as a quieter secondary item.
- Add a compact global-search affordance only if it can reuse existing Explorer search behavior;
  otherwise leave it out of the first redesign pass.
- Replace the filled active pill with a quieter text/underline or bottom-border treatment.

Mobile navigation:

- Replace horizontal overflow with a compact top bar and menu sheet.
- Keep Home/Discover/For You/My Library directly reachable in that sheet.
- Keep Insights secondary.
- Do not add a persistent bottom navigation until usage data shows it is needed.

## 8. Shared Component Plan

Create a small visual foundation before redesigning pages. Do not build a large abstract design
system or introduce a component library.

### Tokens and recipes

- Expand `apps/web/src/app/globals.css` with semantic color, typography, radius, shadow, focus,
  and motion tokens.
- Refactor `apps/web/src/lib/ui.ts` into named recipes for primary/secondary/quiet buttons, links,
  page shells, panels, badges, field controls, and focus styles.
- Remove repeated raw slate/teal class strings gradually as each component is touched.
- Do not require a general `cn()` dependency; template strings are sufficient at current scale.

### Shared components to extract

1. `BookCover` from `book-lens-shell.tsx` into its own file with standard sizes and fallback.
2. `PageIntro` for consistent eyebrow, title, description, and optional actions.
3. `Surface` only if it removes real duplication without hiding semantic HTML.
4. `BookRow` and `BookTile` as the two canonical browsing patterns.
5. `ScoreBadge` for match percentages with accessible text.
6. `ReasonList` for explainability reasons; allow compact and expanded variants.
7. `Field` recipes for inputs/selects rather than a wrapper that obscures labels.
8. `EmptyState` with optional illustration slot, title, description, and action.

Avoid extracting a component for every visual div. The goal is consistency and simpler page code,
not indirection.

## 9. Page Redesign Specifications

### 9.1 Home: a discovery front door

Replace “Discovery dashboard” with an editorial entry point.

Recommended structure:

1. Text-led hero: “Find the book that fits right now.” Short explanation, primary Discover action,
   secondary matches action, and only the approved small bookplate/rule chrome. Do not add a large
   hero image, background illustration, or cover composition.
2. Personalized strip: show top matches when the profile has signal; otherwise show one calm
   onboarding card with “Log three books” and “Set preferences” actions.
3. Cover-led “Highly rated in the catalog” shelf using 4–6 books, not a text-only list.
4. “Browse by feeling” or “Browse by theme” row backed by existing tags/theme capabilities. Do not
   invent unsupported mood metadata.
5. Quiet utility footer/section with catalog size, source, and coverage. Move “Catalog health” out
   of the first viewport and rename it “About this catalog.”

Home should not duplicate all features. Its job is to create interest and direct the next action.

### 9.2 Discover (`/explore`): search first, filters second

Desktop:

- Keep the two-column results/detail model.
- Make search the dominant control at the top.
- Move advanced selects and tag logic into a collapsible filter panel with an active-filter count.
- Replace the split include/minus tag chip with explicit Include / Exclude behavior. A small
  context menu or clearly labeled toggle is preferable to the current unlabeled minus button.
- Increase cover size in results and reduce low-value description/metadata clutter.
- Make the entire result row selectable while keeping its links and log controls valid.
- Keep the selected detail panel sticky, but reduce its nested cards and show the most useful
  recommendation reasons first.

Mobile:

- Use a full-width search field plus a Filters button that opens a modal sheet/drawer.
- Present results as cover-led rows.
- Selecting a book should navigate to the detail route or open a deliberate full-screen panel;
  do not append a long desktop preview below the result list.
- Put active filters in a horizontally scrollable chip row with a visible Clear action.

Optional after the first pass: a grid/list view toggle. Do not include it unless both modes are
fully polished and persist for the session.

### 9.3 Book detail: editorial hero + evidence

- Use a two-column hero on desktop: large cover left; title, author, rating, log action, concise
  description, and key metadata right.
- Make the primary user action (Want to read / Reading / Read) visually clearer than source data.
- Group metadata into a quiet inline fact row instead of four independent mini-cards.
- Keep tags visible but cap the first view and allow expansion.
- Rename “Theme Profile” to “Reading profile” or “Story profile” to avoid confusion with the site's
  visual theme.
- Present theme dimensions as a focused chart/list with a short explanation of how they are derived.
- Put Source and Source ID in a collapsed “Catalog details” disclosure near the bottom.
- Show similar books as cover-led cards/shelf; lead each card with one strong reason and reveal the
  rest on demand.
- Moving Source and Source ID into a disclosure must not remove them from the DOM or alter their
  values. The disclosure must be keyboard operable and use native `<details>/<summary>` unless a
  custom implementation is demonstrably necessary.

### 9.4 For You (`/compatibility`): recommendations, not a score table

- Rename the page in UI to “For You”; keep the route and technical compatibility terminology in
  explanatory copy where useful.
- Lead with book cover, title, author, overall match, and the top one or two human-readable reasons.
- Show dimension percentages as a secondary breakdown, not four tiny boxes on every list item.
- Keep the desktop master/detail model; use a detail drawer or routed detail on mobile.
- Turn “Your profile signal” into a quiet summary near the page intro with a clear Edit action.
- Use a segmented control for sort and a separate filter for read status.
- Preserve and visually improve the current low-signal state. It should feel like guided setup,
  not an error.
- Explain partial scores with one reusable info treatment instead of repeated amber boxes.

### 9.5 My Library (`/profile`): books first, settings second

- Rename the page in UI to “My Library.”
- Create three clear sections or tabs: Reading Log, Taste, Preferences. On desktop, Taste may remain
  a side panel; on mobile, do not stack a long settings form immediately after a long log.
- Add cover thumbnails to log and catalog-search results.
- Consolidate status and rating chip rows into a compact filter bar.
- Keep notes inline but visually subordinate them until focused.
- Turn Taste into a visual summary: top genres, theme lean, usual length, rating behavior.
- Use the same tag and score vocabulary as For You.
- Treat “saved in this browser” as a subtle persistent privacy note, not repeated body copy.
- Add a clear post-save confirmation near the Preferences action in addition to the global toast.

### 9.6 Insights (`/analytics`): reader-facing data story

- Preserve the exact data logic and panel budget defined by `docs/ANALYTICS_PLAN.md`.
- Apply the new type, color, spacing, panel, and chart tokens.
- Use forest, brass, clay, and neutrals consistently by meaning; avoid adding extra chart colors.
- Keep text values next to visual marks and maintain accessible SVG labels.
- Rename only the navigation/page presentation to “Insights”; internal file and type names may stay
  `analytics`.
- Keep this screen visually quieter than Discover and For You. It is supporting evidence, not the
  primary product story.

### 9.7 Empty, loading, warning, and dialog states

- Replace bare loading lines with layout-preserving skeletons for cover rows and primary panels.
- Keep skeleton motion disabled under reduced-motion preferences.
- Standardize warnings and errors with icon, title, concise next step, and `role` semantics.
- Make dialogs use the new surface, focus, button, and typography tokens.
- Preserve focus trapping, Escape behavior, focus restoration, and status announcements.

## 10. Responsive and Accessibility Requirements

Test at minimum at 360, 390, 768, 1024, and 1440 CSS pixels.

Required behavior:

- No horizontal page overflow at 360px.
- Interactive targets should be at least 44px high/wide where practical; compact inline actions
  must still have sufficient padded hit area.
- Visible focus indicators must not rely on color alone and must remain visible on paper, raised,
  forest, and image-backed surfaces.
- Do not encode Include/Exclude, selected state, score quality, or chart series by color alone.
- Maintain one `<h1>` per route and a logical heading sequence.
- Images need useful alt text; decorative cover compositions should be hidden from assistive tech.
- Match percentages and theme bars need adjacent text values or equivalent accessible labels.
- Dialogs/drawers must trap focus, close with Escape, restore focus, and prevent background scroll.
- Support 200% zoom without loss of controls or content.
- Respect reduced motion and increased contrast preferences where feasible.
- Avoid line-clamping essential titles without a title/accessible path to the full value.

## 11. Implementation Phases

### Production implementation guardrails

- Preserve all unrelated user changes in the dirty worktree. Inspect `git status --short` and the
  diff for each target file before editing it; do not overwrite or reformat unrelated work.
- Follow `apps/web/AGENTS.md`. Before changing Next.js code, read the relevant local Next 16.2.9
  documentation under `apps/web/node_modules/next/dist/docs/`; do not rely on remembered APIs.
- Do not edit database migrations, Supabase schema/RLS, pipeline scripts, environment files,
  deployment files, recommendation logic, data loading, or local-profile schema.
- Do not add a UI/component library, icon library, animation library, CSS-in-JS system, or general
  class-name dependency. The approved theme can be implemented with existing Next.js, React,
  Tailwind, CSS, and small repo-native components.
- Do not deploy, change Vercel settings, mutate Supabase, seed data, or alter the public beta during
  this project.
- Do not use broad repository-wide search-and-replace for slate/teal classes. Migrate only the files
  in the active delivery slice, inspect the diff, and verify that slice before continuing.
- Keep server components server-side and client components client-side. Do not add `"use client"`
  merely to simplify styling or animation.
- Preserve semantic elements and native controls. Styling work must not replace working buttons,
  links, selects, inputs, `<details>`, or dialog behavior with non-semantic clickable containers.

### Required preflight reads

Before the first production edit, read these files completely and confirm their purpose:

| File | Confirm before editing |
| --- | --- |
| `apps/web/AGENTS.md` | Local Next.js documentation rule |
| `apps/web/node_modules/next/dist/docs/01-app/01-getting-started/11-css.md` | Supported global/Tailwind CSS pattern |
| `apps/web/node_modules/next/dist/docs/01-app/01-getting-started/13-fonts.md` | Current `next/font` behavior |
| `apps/web/node_modules/next/dist/docs/01-app/01-getting-started/12-images.md` | Cover sizing/loading behavior before considering `Image` |
| `apps/web/node_modules/next/dist/docs/01-app/01-getting-started/03-layouts-and-pages.md` | Layout and server/client boundaries |
| `apps/web/src/app/globals.css`, `apps/web/src/app/layout.tsx`, `apps/web/src/lib/ui.ts` | Current global theme and shared recipes |
| `apps/web/src/lib/filters.ts`, `apps/web/src/lib/pagination.ts` | Explorer semantics and page sizes |
| `apps/web/src/lib/user-profile.ts`, `apps/web/src/hooks/use-user-profile.ts` | Storage schema, normalization, persistence, and cross-tab behavior |
| `apps/web/src/lib/compatibility.ts`, `apps/web/src/lib/compatibility-rankings.ts` | Scoring, low/partial signal, filtering, and sorting behavior |
| `apps/web/src/lib/load-booklens-data.ts`, `apps/web/src/lib/booklens-data.ts` | Supabase/fixture behavior and recommendation limits |
| `docs/ANALYTICS_PLAN.md`, `apps/web/src/lib/analytics.ts` | Analytics authority, data rules, and panel budget |
| All target route/component files for the active slice | Existing states, actions, ARIA, and overlapping user edits |

### Protected behavior modules

The following files are read-only for this redesign. Import and reuse them; do not edit them:

- `apps/web/src/lib/filters.ts`
- `apps/web/src/lib/pagination.ts`
- `apps/web/src/lib/user-profile.ts`
- `apps/web/src/hooks/use-user-profile.ts`
- `apps/web/src/lib/compatibility.ts`
- `apps/web/src/lib/compatibility-rankings.ts`
- `apps/web/src/lib/theme-profile.ts`
- `apps/web/src/lib/analytics.ts`
- `apps/web/src/lib/load-booklens-data.ts`
- `apps/web/src/lib/booklens-data.ts`
- `apps/web/src/lib/supabase/**`

If presentation work appears to require changing one of these files, stop and report the exact
reason before editing it. A visual redesign is not authorization to change behavior.

### Phase 0 — Baseline and visual inventory

1. Capture desktop and mobile screenshots for every route and important state before editing.
2. Record one representative normal, empty/low-signal, loading, and dialog state.
3. Verify current lint/build and note pre-existing failures without modifying unrelated work.
4. Create a checklist of repeated color, type, panel, button, field, cover, and badge patterns.
5. Record `localStorage.getItem("booklens.userProfile.v1")` from the manual-test browser before any
   UI edit. Merely loading or navigating the redesigned app must not change that value.
6. Record the current operation matrix from the regression table below with both an empty profile
   and a populated profile containing each status, a half-star rating, a note, and preferences.

Acceptance: before screenshots, a known-good route matrix, baseline lint/build results, and a saved
profile-storage snapshot exist. If baseline lint/build fails, record the exact failure and do not
attribute it to redesign work.

### Phase 0.5 — Theme test sites and user decision (completed)

Files:

- `prototypes/ui-themes/README.md`
- `prototypes/ui-themes/DECISION.md`
- `prototypes/ui-themes/shared/`
- one directory per theme direction

Work:

1. Build the three isolated themes and required representative screens from Section 5.
2. Generate theme-specific artwork only where it materially demonstrates the direction.
3. Capture the desktop/mobile comparison views and complete the scorecard.
4. Present the comparison to the user and record the selected or hybrid direction.
5. Update this plan so the approved theme—not the initial recommendation—controls Phase 1 onward.

Acceptance met: the user selected the Curated Reading Room, then approved the walnut direction and
requested removal of the large hero artwork in favor of small chrome. The prototypes and decision
record remain available for reference.

### Phase 1 — Theme foundation

Files:

- `apps/web/src/app/globals.css`
- `apps/web/src/app/layout.tsx`
- `apps/web/src/lib/ui.ts`

Work:

1. Add Newsreader and semantic design tokens.
2. Add base body, selection, focus-visible, reduced-motion, and form-control styles.
3. Create the small set of shared class recipes.
4. Implement only the approved small code-native bookplate/rule/wordmark chrome. Do not generate or
   add a hero/background raster asset.
5. Update the page background and global type hierarchy without redesigning route layouts yet.

Acceptance: all current pages still work; tokens meet contrast; no raw hex additions in touched
components unless a data visualization genuinely requires one. No route markup, data flow, client
state, storage behavior, or event handler changes are allowed in this phase.

### Phase 2 — Navigation and shared book primitives

Files:

- `apps/web/src/components/site-nav.tsx`
- `apps/web/src/components/book-cover.tsx` (new)
- `apps/web/src/components/book-row.tsx` (new if duplication justifies it)
- `apps/web/src/components/book-tile.tsx` (new)
- `apps/web/src/components/book-lens-shell.tsx`
- relevant action/dialog components

Work:

1. Implement the desktop and mobile navigation model.
2. Extract and standardize cover rendering/fallback.
3. Add canonical reason, score, button, field, and empty-state treatments.
4. Migrate one low-risk surface first to validate the system.

Acceptance: navigation works with keyboard and touch; covers do not shift layout; shared primitives
handle missing covers and long titles. All existing navigation destinations, book actions, dialog
operations, compatibility links, and cover alt/fallback behavior remain available.

### Phase 3 — Home

Files:

- `apps/web/src/components/home-dashboard.tsx`
- `apps/web/src/components/home-profile-snapshot.tsx`
- `apps/web/src/components/home-top-matches.tsx`
- `apps/web/src/lib/home-summary.ts` only if display selection needs a pure helper

Work:

1. Build the cover-led hero and discovery shelves from existing data.
2. Reorder personalized, discovery, and catalog-information sections.
3. Preserve all data honesty and no-profile states.

Acceptance: the first viewport contains books or a clear setup path, not catalog diagnostics.
Catalog diagnostics, source/fixture badges, coverage values, top tags, profile snapshot, top matches,
and all current Home links must still exist elsewhere on the page with unchanged values and targets.

### Phase 4 — Discover and book detail

Files:

- `apps/web/src/components/book-explorer.tsx`
- `apps/web/src/components/filter-controls.tsx`
- `apps/web/src/components/book-lens-shell.tsx`
- `apps/web/src/components/book-tags.tsx`
- `apps/web/src/app/books/[id]/page.tsx`

Work:

1. Restructure search and filters with an accessible mobile drawer.
2. Redesign result rows and selected-book behavior.
3. Build the editorial book-detail hero and cover-led similar books.
4. Move source metadata into a disclosure.

Acceptance: filter behavior and pagination remain unchanged; mobile never appends an unwieldy
desktop preview; all book actions remain reachable. Search must still cover title, author,
description, and tags; included tags remain AND semantics; excluded tags remain ANY-match rejection;
page size remains 25; tag search/show-more and every active-filter clear path remain operational.

### Phase 5 — For You and My Library

Files:

- `apps/web/src/components/compatibility-page.tsx`
- `apps/web/src/components/profile-page.tsx`
- `apps/web/src/components/log-book-controls.tsx`
- `apps/web/src/components/star-rating-input.tsx`

Work:

1. Add covers and simplify match cards.
2. Move detailed dimensions to the selected-book view.
3. Restructure Profile around log, taste, and preferences.
4. Unify personal-signal language and status controls across both pages.

Acceptance: no compatibility or profile calculation changes; local storage data remains compatible;
the flow is usable with an empty and a populated profile. Storage key/version, half-star ratings,
clear rating, notes, confirmations, cross-tab sync, status/rating filters, all sorts, query-string
selection, hide-read default, partial-signal messaging, and every preference remain unchanged.

### Phase 6 — Insights and system states

Files:

- `apps/web/src/app/analytics/page.tsx`
- `apps/web/src/components/analytics-section.tsx`
- loading, empty, warning, and dialog components

Work:

1. Apply the new theme without changing analytics calculations or panel scope.
2. Standardize loading, empty, error, toast, and modal treatments.
3. Verify charts at narrow widths and with sparse data.

Acceptance: requirements in both this plan and `docs/ANALYTICS_PLAN.md` pass; if they conflict,
the analytics document controls data and panel scope while this document controls global styling.

### Phase 7 — Quality pass

1. Test all routes and states at target widths.
2. Perform keyboard-only and screen-reader smoke tests.
3. Check contrast, reduced motion, 200% zoom, long titles/authors, missing covers, and sparse data.
4. Run lint and production build.
5. Compare after screenshots with the baseline and remove remaining one-off visual recipes.
6. Check image loading, layout shift, route payloads, and unnecessary client-side code.

Acceptance: the Definition of Done below is met.

### Required operation regression matrix

Run this matrix after the slice that touches the route and again in Phase 7. Visual similarity alone
does not count as a pass.

| Area | Operations that must be manually verified |
| --- | --- |
| Global data | Supabase data loads; fixture fallback and warning render when forced; empty catalog renders `EmptyBooksState`; source labels and counts remain truthful |
| Navigation | Every desktop/mobile item reaches the existing URL; active state is correct; keyboard focus remains visible; mobile menu closes and restores focus |
| Home | All four primary links work; catalog/source/coverage/top-tag values remain; empty-profile onboarding works; populated-profile snapshot and top matches appear; featured books link to detail |
| Explorer search | Search still matches title, author, description, and tags; clearing search restores results and page 1 |
| Explorer filters | Decade, length, average rating, rating count, include tags, and exclude tags produce the same result set as baseline; include uses AND; exclude uses ANY rejection |
| Explorer controls | Tag search, show more/fewer, active chips, individual clear, clear all, zero-result state, Previous/Next, page/range labels, row selection, sticky preview, and full-detail links work |
| Book detail | Valid ID renders; invalid ID returns not-found; back link works; all metadata/source fields remain; tags expand; log/rating controls work; story profile and linked similar books remain |
| Add/remove dialog | Initial focus, Tab/Shift+Tab loop, Escape, backdrop click, Cancel, confirm, pending state, error state, and focus restoration behave as before |
| Reading log | Add, remove, and change `want`/`reading`/`read`; set every half-star boundary including 0.5 and 5; clear rating; edit a 280-character note; reload persistence works |
| Profile browsing | Status/rating filters, text filter, updated/rating/title sorts, 10-item pagination, catalog search minimum length, eight-result limit, and already-logged exclusion work |
| Preferences | Favorite genre parsing/deduplication, preferred length, rating floor, pace, Save, confirmation, derived taste, and browser-only privacy copy remain |
| Storage | Key remains `booklens.userProfile.v1`; passive render/navigation does not rewrite data; reload and a second tab receive the same profile; malformed stored data still normalizes safely |
| Compatibility | Empty-profile checklist; valid/invalid `?book=` selection; hide-read default; title/author search; match/title/recent sorts; 25-item cap; partial note; reasons/dimensions; selected panel; log controls |
| Analytics | Three titled sections and no more than four panels; coverage, decades, scatter, recommendation coverage, reasons, and hidden gems match baseline data; sparse fallbacks and links work |
| Responsive/a11y | 360/390/768/1024/1440 widths, 200% zoom, keyboard-only flow, reduced motion, long strings, missing covers, sparse metadata, and no horizontal page overflow |

### Validation commands

Run from `apps/web` after each reviewable slice:

```bash
npm run lint
npm run build
```

Then smoke-test `/`, `/explore`, `/analytics`, `/compatibility`, `/profile`, one valid
`/books/[id]`, and one invalid book ID. A successful HTTP response is necessary but not sufficient;
complete the route's operation checks above. Do not deploy as part of validation.

### Rollback discipline

- Keep each delivery slice independently reviewable and do not start the next slice while the
  current slice has a functional regression.
- Before a slice, record its target-file diff. After it, inspect only the new delta and verify no
  protected module or unrelated user file changed.
- If a slice fails, revert only changes made by that slice using a targeted patch. Do not use
  `git reset --hard`, `git checkout --`, or any command that could discard the user's dirty-worktree
  changes.
- Do not “fix forward” by changing data/scoring/storage logic. Restore the last working presentation
  and report the blocker.

### Stop conditions

Pause implementation and request direction if any of these occur:

- A required feature can be preserved only by changing a protected behavior module or data contract.
- Existing uncommitted user work overlaps a target file in a way that cannot be safely separated.
- The baseline build/lint or a route operation fails and the cause cannot be distinguished from the
  redesign.
- A visual requirement would remove information, change a route, change filter/scoring semantics,
  change storage, add authentication, or require a database/deployment change.
- The selected font cannot be loaded through the documented Next.js pattern without a build or
  network failure; retain the existing font plus a safe serif fallback rather than improvising.
- Responsive behavior would require a new interaction model that is not specified here. Preserve
  the current operation and report the choice instead of inventing one.

### Expected implementation handoff

For every slice, report:

1. Files changed and the user-visible visual outcome.
2. Protected behaviors explicitly rechecked.
3. Lint/build and route/manual checks run, including anything skipped and why.
4. Before/after screenshots at the required widths.
5. Any remaining visual compromises, risks, or stop-condition decisions.
6. Confirmation that no protected behavior modules, data, storage schema, deployment, or unrelated
   user changes were modified.

## 12. Recommended Delivery Slices

Keep reviewable changes small enough that visual regressions can be isolated:

1. Isolated theme test sites + documented user decision.
2. Approved theme tokens + typography.
3. Navigation + cover primitives.
4. Home.
5. Discover + detail.
6. For You + My Library.
7. Insights + state/accessibility polish.

Do not mix recommendation/data-model changes into these slices.

## 13. Definition of Done

- BookLens has one recognizable visual system across all routes.
- At least three isolated theme test sites were reviewed before production implementation, and the
  selected or hybrid direction is documented.
- Home reads as a book-discovery product within the first viewport.
- Every primary discovery or personal-library surface uses book covers when available.
- Missing covers look intentional and preserve layout.
- No large background/hero artwork or raster chrome is added. Any future separately approved image
  is original, responsive, performance-conscious, and nonessential to operating the interface.
- Page, section, card, and metadata hierarchy are visibly distinct.
- Nested borders/cards are materially reduced.
- UI text below 12px is rare and justified.
- Discover filters are clear on desktop and intentionally mobile.
- Include and Exclude actions are understandable without relying on a minus symbol or color.
- Compatibility reasons are more prominent than raw dimension percentages.
- Profile prioritizes books and taste before settings.
- Analytics preserves its current data contract and visual panel budget.
- All current routes, local profile data, filters, pagination, and dialogs continue to work.
- Keyboard, focus, contrast, zoom, reduced-motion, and screen-reader checks pass.
- Lint and production build pass, aside from explicitly documented pre-existing failures.
- Before/after screenshots exist for each route at mobile and desktop widths.

## 14. Deferred Ideas

These may be valuable later but are not required for the visual redesign:

- Dark mode.
- User-selectable themes.
- Social feeds, public profiles, clubs, or follows.
- A persistent mobile bottom navigation.
- Grid/list view persistence across sessions.
- Large illustration sets or route-specific artwork beyond the small background/chrome system.
- New recommendation dimensions or AI-written summaries.
- Changing the data pipeline to source higher-resolution covers.

## 15. First Implementation Recommendation

On the user's explicit implementation command, start with the baseline capture and operation matrix
in Phase 0; Phase 0.5 is complete. Then implement Phases 1–2 with the locked Curated Reading Room
visual system and redesign Home as the first production proof. Home exercises typography, covers,
navigation, actions, tags, scores, empty states, and responsive shelves without first disturbing the
more interaction-heavy Explorer and Profile screens. Do not continue beyond a slice with a failed
operation check. Once Home passes its full preservation matrix, use the validated primitives to
update the remaining routes in order.
