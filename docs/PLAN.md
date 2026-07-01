# BookLens Project Plan

## Current Goal

Set up the smallest clean foundation for BookLens without overbuilding.

BookLens should start as:

- A clean GitHub repo
- A documented design
- A Python data pipeline
- A minimal Next.js frontend
- Deployment-ready structure

Do not add FastAPI, Modal, Supabase, or LiteLLM until the app clearly needs them.

## Stack Decisions

### Frontend

Use:

- Next.js
- TypeScript
- Vercel deployment

### Backend

Use FastAPI only if a separate API is needed.

Possible reasons to add FastAPI later:

- Recommendation logic becomes too heavy for frontend/server actions
- Python model serving is needed
- Scheduled data refreshes are needed
- Secure server-side access to Supabase is needed

If added, deploy FastAPI on Modal.

### Database, Auth, and Storage

Use Supabase only if the project needs:

- Persistent book data
- User accounts
- Saved lists
- File storage
- Server-side Postgres queries

For the earliest MVP, CSV or static JSON data may be enough.

### LLM Routing

Use LiteLLM only if the product needs model calls.

Do not add LiteLLM for the first version.

## MVP Features

1. Book explorer
2. Search and filters
3. Top tags
4. Book detail view
5. Similar-book recommendations
6. Recommendation explanation chips
7. Basic analytics

## Development Order

1. Finish repo setup
2. Add local development docs
3. Add data pipeline
4. Run demo data pipeline
5. Run live Open Library data collection
6. Generate cleaned dataset
7. Generate top tags
8. Prototype similar-book recommendations
9. Add minimal Next.js frontend
10. Build explorer page
11. Build detail page
12. Build recommendation cards
13. Add analytics view
14. Deploy frontend to Vercel

## Repo Rules

- Keep generated data out of Git unless intentionally adding a small sample fixture
- Never commit secrets
- Commit `.env.example`, not `.env`
- Work from WSL, not Windows paths
- Keep the project small and understandable
