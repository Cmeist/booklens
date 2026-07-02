# BookLens Design Document

## 1. Project Overview

**BookLens** is a portfolio-ready book discovery and recommendation web application. The project focuses on helping readers explore books using structured metadata, strong filtering, popular subject tags, and explainable similar-book recommendations.

The project is intentionally scoped as a professional data product rather than a Goodreads clone. The first version should prove that a reader can search a clean catalog, filter by practical reading criteria, inspect book details, and receive understandable similarity-based recommendations.

## 2. Problem Statement

Many book discovery sites make it difficult to filter large book lists by practical criteria such as genre, subject, publication year, page count, average rating, and rating count. Recommendation tools can also feel opaque because they often provide suggestions without explaining which metadata or preference signals influenced the result.

BookLens addresses this by combining:

- A clean book metadata dataset
- Advanced search and filters
- Top subject/tag discovery
- Similar-book recommendations
- Recommendation explanation chips
- A small analytics surface for data exploration

## 3. Target Users

Primary users are readers who want a faster way to find books that match their interests. Secondary users include students, book-club organizers, librarians, reviewers, and anyone who wants to explore book metadata interactively.

The project is also designed for technical reviewers and recruiters. It should demonstrate data cleaning, feature engineering, recommendation-system thinking, frontend implementation, deployment readiness, and careful secrets handling.

## 4. Product Goals

1. Build a searchable and filterable book catalog.
2. Support practical filters using title, author, description, tags, year, page count, rating count, and average rating.
3. Show the top 10 or so most popular tags/subjects in the dataset.
4. Recommend similar books from a selected seed book.
5. Explain recommendations with simple reason chips.
6. Provide a small analytics view based on tags, years, ratings, and page counts.
7. Keep the codebase clean enough to continue developing in Cursor with WSL2.
8. Prepare the project for deployment without prematurely adding unnecessary infrastructure.

## 5. Non-Goals for Version 1

BookLens v1 will not attempt to replace Goodreads or build a full social network. The first version should avoid features that add complexity before the core data product is working.

Out of scope for v1:

- Full social reviews/comments
- Follower systems
- User-generated public review moderation
- Goodreads import
- Mobile app
- Book purchasing/affiliate links
- LLM-generated content unless a clear product need appears
- FastAPI backend unless the frontend actually needs a separate API
- Supabase auth/database/storage unless persistent app data is needed

## 6. Core Book Data Fields

The initial dataset should prioritize these fields:

| Field | Purpose |
| --- | --- |
| `title` | Search, display, and book identity |
| `author` | Search, display, filtering, and recommendation signal |
| `description` | Recommendation similarity and detail-page content |
| `tags` / `subjects` | Filtering, top-tags feature, and recommendation signal |
| `publication_year` | Era/decade filtering and analytics |
| `page_count` | Practical reader filter and recommendation signal |
| `rating_count` | Popularity/confidence signal |
| `average_rating` | Quality signal |
| `cover_url` | Product polish for cards and detail pages |
| `source_id` | Traceability to source records |

## 7. Essential Features

### 7.1 Advanced Book Explorer

The Explore page is the main product surface. Users should be able to search and filter a book catalog using the agreed metadata fields.

Essential filters:

- Title search
- Author search/filter
- Genre or subject tag
- Publication year or decade
- Page count range
- Average rating range
- Rating count range

Essential sort options:

- Relevance
- Average rating
- Rating count / popularity
- Publication year
- Page count

### 7.2 Top Tags Section

BookLens should show the top 10 or so most common tags/subjects from the cleaned dataset.

This feature should appear in at least one of these places:

- Home page as “Popular Reading Categories”
- Explore page sidebar as “Top Tags”
- Analytics page as a bar chart

Each tag should be clickable and should filter the Explore page to matching books.

### 7.3 Book Detail Page

Each book card should link to a detail page.

Essential detail fields:

- Cover image, if available
- Title
- Author
- Description
- Tags/subjects
- Publication year
- Page count
- Average rating
- Rating count
- Similar books

### 7.4 Similar-Books Recommendation Tool

Users should be able to select a book and view similar recommendations.

The v1 recommendation system should be content-based and use available metadata rather than requiring user accounts or rating histories.

Recommended similarity inputs:

- Description text
- Shared tags/subjects
- Title keywords
- Author signal, where relevant
- Publication year proximity
- Page count proximity
- Average rating and rating count as supporting signals

### 7.5 Recommendation Explanation Chips

Each recommendation card should include short explanation chips such as:

- Shared tag
- Similar subjects
- Similar description keywords
- Similar page count
- Same era
- Highly rated
- Popular with many ratings

Example recommendation explanation:

> Similar because both books share fantasy, coming-of-age, magic, and young adult tags.

### 7.6 Small Analytics View

The analytics view should stay focused. Recommended charts:

1. Top 10 tags
2. Average rating by tag
3. Publication year distribution
4. Page count vs. average rating
5. Rating count vs. average rating

The goal is to show data-analysis skill without turning the app into a large BI dashboard.

## 8. Lower-Priority Features

### Hidden Gems

The hidden-gem concept is useful, but it should be a lower-priority Phase 2 feature rather than a central MVP pillar.

A later hidden-gem feature could identify books with strong average ratings and lower rating counts, while avoiding books with too few ratings to be trustworthy.

### Saved Lists and User Accounts

Saved lists are useful, but they require persistence and possibly authentication. Add them only after the catalog, filters, detail pages, and similar-book recommendations are working.

### Collaborative Filtering

Collaborative filtering is a good stretch goal, but it requires a reliable ratings dataset and more evaluation work. The first recommendation system should be content-based.

## 9. Data Pipeline Design

The data pipeline should remain the foundation of the project.

### 9.1 Extract

Collect book metadata from API-based or downloadable public sources. Avoid scraping pages where terms, robots rules, or API restrictions make scraping inappropriate.

The current repo supports:

- Offline fixture data for pipeline testing
- Open Library collection
- Optional Google Books enrichment, if configured

### 9.2 Clean

Cleaning should include:

- Normalize titles and authors
- Remove duplicate records where possible
- Standardize tags/subjects
- Parse publication years
- Normalize page counts
- Handle missing descriptions, covers, ratings, and counts
- Produce a data quality report

### 9.3 Transform

Transformations should include:

- Generate a cleaned `books_clean.csv`
- Generate `top_tags.csv`
- Create combined text fields for recommendation similarity
- Create a sample recommendation output for testing

### 9.4 Load / Serve

For the first version, the frontend can use a small static JSON export generated from the cleaned CSV.

Supabase should become the source of truth only when the app needs persistent app data, auth, storage, or production database queries.

## 10. Recommendation System Design

### 10.1 MVP Recommendation Method

Use content-based similarity first.

Recommended approach:

1. Combine title, author, description, and tags into a recommendation text field.
2. Clean and tokenize the text.
3. Use TF-IDF vectorization.
4. Use cosine similarity to find related books.
5. Filter out duplicate editions or the same book.
6. Generate explanation chips from overlapping tags and metadata similarities.

### 10.2 Recommendation Inputs

The recommender should use:

- Title
- Author
- Description
- Genre / subject tags
- Publication year
- Page count
- Rating count
- Average rating

### 10.3 Evaluation Ideas

Simple offline evaluation can include:

- Manual inspection of sample recommendations
- Tag overlap counts
- Diversity of recommended tags
- Average rating distribution of results
- Rating count distribution of results
- Coverage across different tags/genres

## 11. Application Architecture

### 11.1 Smallest Clean Setup

The smallest clean setup for this project is:

- Python data pipeline at the repo root
- Minimal Next.js frontend under `apps/web`
- Static/generated data files during early development
- Supabase only when persistent data, auth, or storage is needed
- FastAPI/Modal only when a separate backend/API is needed
- LiteLLM only when LLM/model calls become part of the app

This avoids blindly copying unrelated structure from another repo and keeps the project focused on the current product needs.

### 11.2 Frontend

- Framework: **Next.js**
- Deployment: **Vercel**
- Location: `apps/web`
- Styling: simple modern UI, likely CSS modules, Tailwind, or plain CSS initially
- Browser-safe environment variables must use `NEXT_PUBLIC_*`

Likely frontend env vars:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=
```

`NEXT_PUBLIC_API_URL` is only needed if a separate backend/API is created.

### 11.3 Backend/API

- Framework: **FastAPI**
- Deployment: **Modal**
- Add only if the app needs a backend/API

Do not add FastAPI until there is a clear need such as:

- Server-side recommendation endpoints
- Protected Supabase service-role access
- Scheduled enrichment jobs
- Long-running Python jobs
- Backend-only API key usage
- Database writes that should not happen from the browser

Local backend dev command should be similar to:

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Likely Modal/backend env vars:

```bash
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_URL=
MY_APP_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

Provider keys are only needed if model calls are added.

### 11.4 Database, Auth, and Storage

- Platform: **Supabase**
- Use Supabase Auth only if users/accounts are needed.
- Use Supabase Postgres as the source of truth if persistent app data is needed.
- Use Supabase Storage for uploads/assets if needed.
- Use migrations for schema changes.
- Do not rely on ORM auto-generated production schema as the source of truth.

Frontend-safe Supabase variables:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

Server-only Supabase variables:

```bash
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_URL=
```

Rules:

- Service-role keys must never be exposed to the browser.
- Database URLs must be server-only.
- Real values belong only in local `.env` files and deployment dashboards.
- Commit only `.env.example` with placeholder names.

### 11.5 Optional LLM Routing

- Tool: **LiteLLM**
- Use only if the app needs LLM/model calls.
- Do not include LiteLLM in the first metadata/recommendation MVP.
- If added later, provider keys must stay server-side only.

Possible future LLM features:

- Natural-language query parsing
- Recommendation explanation polishing
- Reading mood extraction
- Book-list summarization

## 12. Local Development Environment

The developer environment should be:

- Windows 11 host
- WSL2 Ubuntu runtime
- Cursor editor using WSL integration

Important rules:

- Work inside WSL2 Ubuntu, not directly under `/mnt/c/...`.
- Keep the repo somewhere like `~/dev/booklens`.
- Open the WSL folder from Cursor using the WSL integration.
- Run terminal commands inside WSL.
- Use Linux-side tooling only: Node, npm/pnpm, Python, uv, git, make.
- Avoid Windows Node/npm/Python bleeding into the WSL PATH.
- Do not run `npm install` from Windows tooling inside the WSL repo.

Recommended tooling inside WSL:

- `git`
- `make`
- `curl`
- `uv`
- Node 20+ via `nvm`
- Python 3.12 if using FastAPI or the Python pipeline

Confirm tools resolve to Linux paths:

```bash
which node
which npm
which python
which uv
which git
```

Good paths look like:

- `~/.nvm/...`
- `/usr/bin/...`
- `~/.local/bin/...`

Bad paths look like:

- `/mnt/c/Program Files/...`
- `/mnt/c/Users/...`

If package binaries break, for example `node_modules/.bin/next` becomes a regular file instead of a symlink/executable, assume Windows npm polluted the install. Delete `node_modules` and reinstall from a clean WSL terminal using Linux npm.

## 13. Secrets Policy

Never commit:

- `.env` files
- API keys
- Supabase service-role keys
- Database URLs
- Vercel credentials
- Modal credentials
- Deployment credentials
- Model provider keys

Commit only:

- `.env.example` files with placeholder variable names
- Documentation describing required variables

## 14. Deployment Strategy

### 14.1 GitHub

GitHub should be the source of truth for code and project history.

Recommended workflow:

1. Work locally in WSL/Cursor.
2. Commit changes with clear messages.
3. Push to GitHub.
4. Connect Vercel to the GitHub repo for frontend deployments.
5. Add Modal only when backend deployment is actually needed.

### 14.2 Vercel

Use Vercel for the Next.js frontend.

Likely Vercel env vars:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=
```

Rules:

- Configure real values in the Vercel dashboard.
- Use browser-safe `NEXT_PUBLIC_*` values only for public frontend config.
- Keep privileged secrets out of frontend code unless they are server-only env vars used by Next.js server actions or route handlers.

### 14.3 Supabase

Use Supabase for auth, database, and storage only when needed.

Use cases:

- Auth: saved reading lists or user profiles
- Postgres: production book catalog or app-owned data
- Storage: uploaded assets or cached app files

Schema changes should use migrations.

### 14.4 Modal

Use Modal for FastAPI or Python backend services only when needed.

Rules:

- Store secrets in Modal Secrets, not committed files.
- Backend should read configuration from environment variables.
- Do not deploy until the developer explicitly confirms deployment is desired.

Likely Modal/backend env vars:

```bash
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_URL=
MY_APP_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

## 15. Repo Structure

Recommended current structure:

```text
booklens/
  apps/
    web/                         # Next.js frontend
  data/
    fixtures/                    # Offline demo data
    raw/                         # Generated raw files, not committed except .gitkeep
    processed/                   # Generated processed files, not committed except .gitkeep
  docs/
    DESIGN.md                    # This design document
    PLAN.md                      # Shorter implementation plan
    LOCAL_DEV_WSL_CURSOR.md       # Local environment checklist
  scripts/                       # Python data pipeline scripts
  notebooks/                     # Optional analysis notebooks
  run_pipeline.py                # One-command pipeline runner
  pyproject.toml                 # uv/Python project config
  requirements.txt               # pip fallback dependencies
  Makefile                       # Common commands
  .env.example                   # Placeholder env vars only
  .gitignore
```

## 16. MVP Implementation Sequence

1. Confirm WSL/Cursor environment is clean with `make check-env`.
2. Run the offline pipeline demo.
3. Run a small live Open Library collection.
4. Inspect `books_clean.csv`, `top_tags.csv`, and `data_quality_report.txt`.
5. Generate a small static JSON export for the web app.
6. Build the first Explore page from static data.
7. Add Top Tags UI.
8. Add Book Detail pages.
9. Add Similar Books page/cards using recommendation output.
10. Add explanation chips.
11. Add a small analytics page.
12. Deploy the frontend to Vercel.
13. Add Supabase only when persistent data/auth/storage is needed.
14. Add FastAPI/Modal only when a separate API is needed.
15. Add LiteLLM only if model calls become part of the app.

## 17. Resume Value

This project can support strong resume bullets such as:

- Built a full-stack book discovery web app using Next.js, Python, and public book metadata.
- Created a data pipeline to collect, clean, normalize, and analyze structured book records.
- Developed advanced filtering across title, author, tags, publication year, page count, rating count, and average rating.
- Built an explainable similar-book recommendation prototype using metadata and text similarity.
- Generated top-tag analytics and interactive discovery features from cleaned book data.
- Prepared a deployment-ready foundation using Vercel, Supabase planning, WSL2, Cursor, and secure environment-variable practices.

## 18. Success Criteria

The MVP is successful if:

1. The pipeline produces a clean book catalog.
2. The app can display and filter books using the core fields.
3. The top 10 tags are visible and clickable.
4. Book detail pages are useful and visually clean.
5. Similar-book recommendations feel understandable.
6. Recommendation cards include explanation chips.
7. The app has a small analytics view.
8. The repo is clean, documented, and safe for public GitHub.
9. No secrets are committed.
10. The frontend can be deployed to Vercel.

## 19. Final Product Vision

BookLens should feel like a smarter book discovery layer: simple enough to use quickly, structured enough to filter effectively, and transparent enough that users understand why each recommendation appears.

The strongest version is not a Goodreads clone. It is a focused data product that turns messy book metadata into a polished, searchable, explainable reading-discovery tool.
