# BookLens Project Plan

## Current Goal

Build the smallest polished BookLens MVP that proves the portfolio concept:

- A deterministic Python data pipeline
- A clean static-data contract for the web app
- A useful Next.js explorer/detail/analytics experience
- Explainable similar-book recommendations
- No FastAPI, Modal, Supabase, auth, or LiteLLM yet

This repo already has a Python project, a minimal Next.js app in `apps/web`, and starter scripts in `scripts`. Cursor Composer should improve those pieces rather than introduce a new architecture.

## Non-Goals For This Pass

Do not add these unless a later plan explicitly asks for them:

- FastAPI backend
- Modal deployment
- Supabase database, auth, storage, or migrations
- LiteLLM or model-provider integrations
- User accounts, saved lists, comments, reviews, or social features
- Large committed datasets

## Current Repo State

Important existing files:

- `docs/DESIGN.md`: product/design source of truth
- `docs/LOCAL_DEV_WSL_CURSOR.md`: local environment guidance
- `pyproject.toml`: Python dependencies already include pandas, requests, scikit-learn, python-dotenv, and ruff
- `scripts/run_pipeline.py`: demo pipeline that currently writes sample CSV outputs
- `scripts/collect_openlibrary.py`: Open Library collector that writes raw CSV data
- `apps/web`: Next.js + TypeScript app created from the starter template
- `.gitignore`: already excludes `.env`, `.venv`, `node_modules`, `.next`, and generated `data/raw` / `data/processed`

Known gap: `scripts/collect_openlibrary.py` collects raw Open Library rows, but `scripts/run_pipeline.py` does not yet clean that live raw data or produce web-ready JSON/recommendations.

## Architecture Decision

Use a static-data MVP:

1. Python scripts collect and process book data.
2. The pipeline exports a small committed frontend fixture for the deployed demo.
3. The Next.js app imports that fixture directly and renders the app.
4. Similarity is precomputed by Python and stored with simple explanation reasons.

This keeps the Vercel deployment simple and avoids needing a database or API server.

## Data Policy

Generated data stays out of Git by default:

- Keep `data/raw/` ignored.
- Keep `data/processed/` ignored.
- Commit only a small curated web fixture under `apps/web/src/data/`.

Recommended committed fixture files:

- `apps/web/src/data/books.sample.json`
- `apps/web/src/data/top-tags.sample.json`
- `apps/web/src/data/recommendations.sample.json`

The fixture should be small enough for portfolio/demo use, roughly 50-200 books. If live collection produces sparse metadata, prefer a smaller but cleaner dataset over a larger noisy one.

## Data Contract

All frontend book records should use this shape:

```ts
export type Book = {
  id: string;
  title: string;
  author: string;
  description: string;
  tags: string[];
  publicationYear: number | null;
  decade: string | null;
  pageCount: number | null;
  ratingCount: number | null;
  averageRating: number | null;
  coverUrl: string | null;
  source: string;
  sourceId: string;
};
```

Recommendation records should use:

```ts
export type BookRecommendation = {
  bookId: string;
  similarBookId: string;
  score: number;
  reasons: string[];
};
```

Top tag records should use:

```ts
export type TopTag = {
  tag: string;
  bookCount: number;
};
```

Reason labels should be short and user-facing:

- `Shared tag`
- `Similar description`
- `Same author`
- `Same publication era`
- `Similar length`
- `Similar rating profile`

## Implementation Phases For Cursor Composer

### Phase 1: Tighten Local Docs And Commands

Goal: make the project easy to run from WSL/Cursor.

Tasks:

1. Expand `docs/LOCAL_DEV_WSL_CURSOR.md` into a complete checklist:
   - confirm repo is under `~/dev/booklens`, not `/mnt/c/...`
   - run `make check-env`
   - install Python deps with `uv sync`
   - install frontend deps from `apps/web` with `npm install`
   - run `make pipeline-demo`
   - run `make web-dev`
   - run `make web-build`
2. Update `README.md` with short setup and run commands.
3. Keep all instructions WSL-first and avoid Windows tool paths.

Acceptance criteria:

- A new contributor can follow docs from a fresh clone.
- Docs mention that `.env` is local only and `.env.example` is safe to commit.

### Phase 2: Build The Data Pipeline

Goal: create one reliable pipeline command that can use demo data or Open Library raw data and export frontend-ready fixtures.

Tasks:

1. Refactor `scripts/run_pipeline.py` so it can:
   - run with built-in demo data by default
   - optionally read `data/raw/openlibrary_books.csv` when present or when a flag is passed
   - normalize column names and value types
   - convert semicolon-delimited tags into cleaned tag lists
   - generate stable `id` values from source/source_id or title/author
   - drop rows missing title or author
   - keep rows with missing rating/page metadata, using `null` in JSON
   - write `data/processed/books_clean.csv`
   - write `data/processed/top_tags.csv`
   - write `data/processed/recommendations.csv`
   - write `data/processed/data_quality_report.txt`
2. Add web export outputs:
   - `apps/web/src/data/books.sample.json`
   - `apps/web/src/data/top-tags.sample.json`
   - `apps/web/src/data/recommendations.sample.json`
3. Use scikit-learn TF-IDF on descriptions plus simple weighted metadata signals for similarity.
4. Generate up to 5 similar books per book.
5. Generate explanation reasons from actual feature overlap, not random labels.
6. Keep network access only in `scripts/collect_openlibrary.py`; `scripts/run_pipeline.py` should be deterministic once raw data exists.

Suggested similarity logic:

- Description similarity: TF-IDF cosine similarity
- Shared tags: Jaccard overlap
- Same author: exact normalized author match
- Same era: same decade
- Similar length: page counts within roughly 15%
- Similar rating profile: average rating within 0.25 and rating counts in a comparable order of magnitude

Acceptance criteria:

- `make pipeline-demo` succeeds without network access.
- The three `apps/web/src/data/*.sample.json` files are written and valid JSON.
- Missing Open Library ratings/page counts do not crash the pipeline.
- The quality report includes row count, missing-field counts, top tags, and number of recommendations.

### Phase 3: Replace The Next.js Starter With The App Shell

Goal: remove the starter page and create a real BookLens first screen.

Tasks:

1. Create TypeScript data types, for example `apps/web/src/lib/types.ts`.
2. Create data loading helpers, for example `apps/web/src/lib/data.ts`, that import the sample JSON fixture.
3. Replace `apps/web/src/app/page.tsx` with the actual app:
   - header/title area
   - search input
   - filter controls
   - top tag bar
   - book result list/grid
   - selected-book detail panel or route link
   - analytics section
4. Avoid a marketing landing page. The first viewport should be the usable explorer.
5. Keep the design polished but restrained, suitable for a data analytics portfolio project.

Acceptance criteria:

- No Next.js starter logo/copy remains.
- The app works with only the committed sample JSON fixture.
- `npm run lint` passes in `apps/web`.
- `npm run build` passes in `apps/web`.

### Phase 4: Book Explorer

Goal: make browsing and filtering useful.

Tasks:

1. Add client-side state for:
   - text search across title, author, description, and tags
   - tag filter
   - decade/year filter
   - page count range
   - average rating minimum
   - rating count minimum
2. Show result count and active filter chips.
3. Make top tags clickable and connected to the explorer filter.
4. Handle null metadata gracefully with labels such as `Unknown year`, not broken UI.
5. Ensure all filter controls work on mobile and desktop.

Acceptance criteria:

- Combining multiple filters narrows the list correctly.
- Clearing filters restores the full list.
- Empty states are helpful and do not look broken.

### Phase 5: Book Detail And Recommendations

Goal: make similar-book recommendations explainable.

Tasks:

1. Add a book detail experience using either:
   - a dynamic route like `apps/web/src/app/books/[id]/page.tsx`, or
   - an in-page selected book panel if that keeps the MVP simpler.
2. Show:
   - cover when available
   - title
   - author
   - description
   - tags
   - publication year
   - page count
   - rating count
   - average rating
3. Show up to 5 similar books using `recommendations.sample.json`.
4. Each recommendation card must include reason chips from the `reasons` array.

Acceptance criteria:

- Every book can be opened or selected.
- Similar books never include the selected book itself.
- Recommendation cards still look good with 1-2 reason chips and with 4-5 reason chips.

### Phase 6: Analytics

Goal: add lightweight analytics without overbuilding.

Tasks:

1. Add analytics from the sample fixture:
   - top tags
   - average rating by tag when enough rating data exists
   - publication year or decade distribution
   - page count vs average rating
   - rating count vs average rating
2. Keep charts simple. Use CSS/SVG or add a small chart dependency only if it makes implementation clearly cleaner.
3. Show unavailable-data states when Open Library fields are sparse.

Acceptance criteria:

- Analytics section renders with demo data.
- Sparse live data does not produce misleading charts.
- The charts support the portfolio story rather than overwhelming the explorer.

### Phase 7: Polish And Verification

Goal: make the MVP feel intentionally built.

Tasks:

1. Review spacing, typography, colors, responsive behavior, and empty states.
2. Avoid a one-note palette. Keep the UI readable and professional.
3. Add loading/error-safe UI only where it is relevant to the static app.
4. Run validation commands:
   - `make pipeline-demo`
   - `uv run ruff check .`
   - `cd apps/web && npm run lint`
   - `cd apps/web && npm run build`
5. Update docs if commands or file locations changed.

Acceptance criteria:

- All validation commands pass.
- The app can be deployed to Vercel as a static Next.js app using committed fixture data.
- No secrets or large generated datasets are committed.

## Cursor Composer Guardrails

When implementing:

- Prefer small, coherent commits or change sets.
- Follow the existing repo layout.
- Do not create a backend folder yet.
- Do not add database clients yet.
- Do not commit `.env` or generated `data/raw` / `data/processed` files.
- Do not remove `.gitignore` protections for generated data.
- Do not depend on Windows paths or Windows-installed Node/Python.
- If adding frontend dependencies, keep them minimal and explain why.
- If Open Library data is sparse, make the UI honest about missing fields instead of fabricating ratings or page counts.

## Cursor Composer Prompts

Use one phase per Composer session. Keep the prompt narrow, then use the handoff template below so another reviewer can check the result before moving on.

### Phase 1 Prompt

```text
You are implementing Phase 1 only from docs/PLAN.md for the BookLens project.

Before editing, read:

- docs/DESIGN.md
- docs/PLAN.md
- docs/LOCAL_DEV_WSL_CURSOR.md
- README.md
- Makefile
- pyproject.toml
- apps/web/package.json

Goal:

Make the local development instructions clear, complete, and usable for a Windows 11 + WSL2 + Cursor workflow. This is a documentation/setup pass only.

Scope:

- Update README.md with concise project overview, repo structure, setup steps, common commands, and current MVP direction.
- Expand docs/LOCAL_DEV_WSL_CURSOR.md into a complete local setup checklist.
- Keep all instructions WSL-first.
- Explain that the repo should live under a Linux path such as ~/dev/booklens, not /mnt/c/...
- Explain how to confirm tool paths with make check-env.
- Include Python setup with uv sync.
- Include frontend setup from apps/web with npm install.
- Include demo pipeline command with make pipeline-demo.
- Include frontend dev/build commands with make web-dev and make web-build.
- Mention that .env is local only, .env.example is safe to commit, and real secrets must never be committed.
- Mention that generated data/raw and data/processed outputs are ignored by Git.
- Keep references to FastAPI, Modal, Supabase, and LiteLLM as future-only/non-goals for this pass.

Do not:

- Do not implement pipeline logic.
- Do not modify scripts/run_pipeline.py or scripts/collect_openlibrary.py.
- Do not modify the Next.js UI.
- Do not add dependencies.
- Do not add backend services.
- Do not add Supabase, Modal, FastAPI, or LiteLLM.
- Do not remove .gitignore protections.
- Do not commit generated data.

Preferred files to edit:

- README.md
- docs/LOCAL_DEV_WSL_CURSOR.md

Only edit docs/PLAN.md if you find a contradiction that would block Phase 1.

Validation:

- Run or inspect enough to confirm the documented commands match the repo.
- If you run commands, prefer:
  - make check-env
  - make pipeline-demo
- Do not run network-dependent commands unless needed.
- Do not run npm install unless dependencies are missing and I explicitly approve it.

Output:

After editing, provide a handoff using the Phase Handoff Template in docs/PLAN.md.
Include changed files, exact commands run, command results, unresolved questions, and recommended next step.
```

### Phase Handoff Template

Use this after every Composer phase so the next reviewer can check the work quickly.

```markdown
## Phase Handoff

### Phase

Phase number and name:

### Summary

Briefly describe what changed and why.

### Files Changed

- `path/to/file`: short description of the change

### Commands Run

- `command`: pass/fail/not run, with a short note

### Acceptance Criteria Check

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

### Scope Check

- [ ] Stayed within the requested phase
- [ ] Did not add FastAPI, Modal, Supabase, LiteLLM, or backend services
- [ ] Did not commit secrets or generated large data
- [ ] Did not remove `.gitignore` protections

### Important Decisions

List any implementation or documentation choices that a reviewer should know about.

### Gaps Or Risks

List anything incomplete, uncertain, skipped, or needing review.

### Next Recommended Phase

State the next phase to implement and why.
```

## Useful Commands

From the repo root:

```bash
make check-env
uv sync
make pipeline-demo
uv run ruff check .
```

From `apps/web`:

```bash
npm install
npm run dev
npm run lint
npm run build
```

Optional live collection command:

```bash
uv run python scripts/collect_openlibrary.py --contact you@example.com --limit-per-subject 25
```

After live collection, rerun the pipeline command that Cursor implements for Open Library input.

## Definition Of Done

The MVP pass is done when:

- The Python pipeline produces clean processed data and committed sample JSON fixtures.
- The web app renders a usable explorer as the first screen.
- Search, filters, top tags, detail view, recommendations, reason chips, and analytics all work.
- The app builds successfully.
- Documentation explains how to reproduce the workflow from WSL/Cursor.
- The repo remains small, understandable, and free of secrets.
