# BookLens Theme Lab

Isolated visual prototypes for choosing BookLens's production theme. Nothing in this directory is
imported by the Next.js application.

## Run locally

From the repository root:

```bash
python3 -m http.server 4173 --directory prototypes/ui-themes
```

Open <http://localhost:4173/>.

## Direct theme URLs

- Curated Reading Room: <http://localhost:4173/curated-reading-room/>
- Modern Book Journal: <http://localhost:4173/modern-book-journal/>
- Intelligent Archive: <http://localhost:4173/intelligent-archive/>

Each direct prototype includes Home, Explore, and Book Detail screens, an artwork toggle, and links
to switch themes without losing the current screen.

## Scope

These are visual-only prototypes backed by a checked-in fixture. They do not query Supabase, read
local profile data, implement real filtering, or import production components. Remote Open Library
cover images are used to demonstrate real-image behavior; every screen also contains an intentional
missing-cover fallback.

The decorative prototype artwork is original and optional. Disable it with the Artwork control to
judge the underlying hierarchy independently.

## Decision process

1. Compare every theme at both viewport presets.
2. Open promising screens at full size.
3. Score the themes in `DECISION.md`.
4. Record one approved theme, a theme with changes, or a deliberate hybrid.
5. Update `docs/UI_REDESIGN_PLAN.md` before production implementation begins.

