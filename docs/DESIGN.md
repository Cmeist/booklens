# BookLens Design Document

## 1. Project Summary

BookLens is an interactive book discovery and recommendation web app.

The goal is to help users find books through better filtering, clearer metadata, popular tags, and explainable similar-book recommendations.

This project is designed as a professional data analytics portfolio project.

## 2. Core Problem

Existing book discovery sites often make it hard to filter large book lists by practical fields like genre, publication year, page count, rating count, and average rating.

Recommendation tools can also feel unclear because they often do not explain why a book was recommended.

BookLens will focus on a smaller, cleaner experience:

- Explore books with useful filters
- View the most common tags
- Find books similar to a selected book
- Show recommendation reasons
- Present the project as a polished web app

## 3. Essential Book Fields

Each book record should prioritize:

- Title
- Author
- Description
- Genre / subject tags
- Publication year
- Page count
- Rating count
- Average rating
- Cover URL, if available

## 4. Essential Features

### 4.1 Book Explorer

Users can browse and search books.

Filters should include:

- Title
- Author
- Genre / subject tag
- Publication year or decade
- Page count range
- Average rating
- Rating count

### 4.2 Top Tags

The app should show the top 10 or so most popular tags in the dataset.

Each tag should be clickable and should filter the book explorer.

### 4.3 Book Detail Page

Each book should have a detail page with:

- Cover
- Title
- Author
- Description
- Tags
- Publication year
- Page count
- Rating count
- Average rating
- Similar books

### 4.4 Similar Books

A user can choose one book and view similar books.

Similarity should use:

- Description text
- Shared tags
- Author
- Publication year
- Page count
- Rating count
- Average rating

### 4.5 Explainable Recommendations

Recommendation cards should include simple reason chips, such as:

- Same tag
- Similar description
- Similar page count
- Similar rating profile
- Same publication era

### 4.6 Analytics

The analytics view should stay focused.

Initial charts:

- Top tags
- Average rating by tag
- Publication year distribution
- Page count vs. average rating
- Rating count vs. average rating

## 5. Lower Priority Features

The Hidden Gems section is useful, but it is not a core MVP feature.

It can be added later as a secondary feature for books with strong average ratings but lower popularity.

User accounts, saved lists, collaborative filtering, AI summaries, and social features should also wait until the main product works.

**Local-first personalization (shipped):** `/profile` stores a reading log and preferences in the browser (`localStorage`). Compatibility scoring uses that local profile — no Supabase Auth required. Cloud sync remains a later option.

## 6. Technical Stack

### Frontend

- Next.js
- TypeScript
- Deployed on Vercel

### Backend

Use FastAPI only if a separate backend/API is needed.

If used:

- FastAPI
- Python
- Deployed on Modal

### Database, Auth, and Storage

Use Supabase if the app needs persistent data, user accounts, or file storage.

Supabase can provide:

- Postgres database
- Auth
- Storage

Schema changes should use migrations. Do not rely on ORM auto-generated production schema as the source of truth.

### Optional LLM Routing

Use LiteLLM only if the app needs model calls.

Do not add LiteLLM unless there is a clear product need.

## 7. Local Development Environment

The project will be developed using:

- Windows 11 host machine
- WSL2 Ubuntu local runtime
- Cursor editor
- GitHub source control

Rules:

- Work inside WSL2 Ubuntu, not directly under `/mnt/c/...`
- Keep the repo in a path like `~/dev/booklens`
- Open the WSL folder from Cursor using the WSL integration
- Run terminal commands inside WSL
- Use Linux-side tools only: Node, npm, Python, uv, git, and make
- Do not run `npm install` from Windows tooling inside the WSL repo

Good tool paths look like:

- `/usr/bin/...`
- `~/.nvm/...`
- `~/.local/bin/...`

Bad tool paths look like:

- `/mnt/c/Program Files/...`
- `/mnt/c/Users/...`

## 8. Secrets Policy

Never commit:

- `.env` files
- API keys
- Supabase service-role keys
- Database URLs
- Deployment credentials
- Provider API keys

Commit only `.env.example` files with placeholder values.

Frontend-safe environment variables may include:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL`

Server-only variables may include:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL`
- Backend API secrets
- Model provider keys

Service-role keys and database URLs must never be exposed to browser code.

## 9. Deployment Plan

### Vercel

Use Vercel for the Next.js frontend.

Configure only safe public variables in frontend code.

### Supabase

Use Supabase only when the app needs database, auth, or storage.

### Modal

Use Modal only if the project needs a Python/FastAPI backend.

Do not deploy to Modal until deployment is explicitly desired.

## 10. MVP Build Order

1. Create clean repo foundation
2. Add design and planning docs
3. Add data pipeline
4. Collect and clean starter book data
5. Generate top tags
6. Prototype similar-book recommendations
7. Add Next.js frontend
8. Build book explorer page
9. Build book detail page
10. Build similar-books page
11. Add basic analytics
12. Deploy frontend to Vercel
