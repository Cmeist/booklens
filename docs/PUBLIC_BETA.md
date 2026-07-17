# BookLens Public Beta Handoff

Friend-testing beta of the current workspace against hosted Supabase.

## Canonical URL

**https://booklens-coy44.vercel.app**

Anonymous access is enabled for Production. Preview deployments remain SSO-protected.

## Deployed artifact

| Item | Value |
|------|-------|
| Production deployment | `dpl_BXknukPJ4jxGP9vwSCpMgz8e6s6n` |
| Production URL | https://booklens-bn7vbkypu-coy44.vercel.app |
| Promoted from preview | https://booklens-nfb0xk1zh-coy44.vercel.app (`dpl_91Aj1V2QRzeobUgCocwk6ZZqsoRq`) |
| Inspect | https://vercel.com/coy44/booklens/BXknukPJ4jxGP9vwSCpMgz8e6s6n |
| Vercel project | `booklens` (`prj_F09FDIfgyMAA2T4jAxszsig6umBr`) |
| Team | `coy44` (`team_RRvmOseR6F70Q2c4vnDuzSG6`) |
| Supabase project | `BookLens` (`ickeyhuybqtpzdwypzsn`) |

### Source manifest (dirty workspace deploy)

- Branch: `feature/data-pipeline-live`
- HEAD: `109ade7d7a0ec6d2f46dbf2328b06e8d22602d90`
- Included local changes at deploy time:
  - Analytics redesign (`analytics.ts`, `analytics-section.tsx`, `analytics/page.tsx`, `ANALYTICS_PLAN.md`)
  - Compatibility preferred-length display fix (`compatibility-page.tsx`)
  - Home summary / snapshot / top-matches work
  - Paginated Supabase loader (`load-booklens-data.ts`)
- No commit was required for this current-workspace beta.

## Catalog gate

| Check | Result |
|-------|--------|
| SQL counts | 1,122 books · 5,512 recommendations · 35,280 book_tags |
| Paginated PostgREST load | 1,122 unique books · 5,512 unique rec pairs · 100 top tags |
| Thresholds | ≥1,100 books and ≥5,000 recommendations |

Loader change: `apps/web/src/lib/load-booklens-data.ts` now pages `books_with_tags` and `book_recommendations` in batches of 500 with stable order tie-breakers, and bounds `top_tags` to 100.

## Environment / security

- Vercel Production + Preview have only:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- No `SUPABASE_DB_URL`, service role, Google Books, or contact-email secrets on Vercel.
- Those public vars are marked **Sensitive** in Vercel (empty on `env pull`; values still inject at build/runtime).
- Supabase advisories kept as-is:
  - No-policy RLS on `book_sources`, `book_isbns`, `ingestion_runs` (intentional private tables)
  - Follow-up: mutable `set_updated_at` search_path warning
- Popularity-signals migration still absent on hosted DB; frontend does not require it.

## Protection

- SSO `deploymentType`: **`preview`** (Production aliases public; previews still SSO).
- Verified: anonymous `GET https://booklens-coy44.vercel.app/` → HTTP 200 (no SSO redirect).
- Verified: preview URL still redirects to Vercel SSO.

## Checks run

1. `cd apps/web && npm run lint` — pass
2. `cd apps/web && npm run build` — pass
3. Catalog pagination verification against hosted BookLens — pass
4. Preview smoke (authenticated share cookie): `/`, `/explore`, `/analytics`, `/compatibility`, `/profile`, book detail with similar books — pass; Data Supabase; 1,122 books
5. Promote preview → production — done
6. Anonymous production smoke: routes 200; home 1,122 IDs; analytics badge `1122 books · Supabase`; book detail shows similar — pass
7. Runtime errors (1h window) — none

## Beta notes for friends

- Profile / preferences live in **browser localStorage** only. They do not sync across devices or users.
- Early beta: catalog and recommendations may change.
- Supabase-backed pages can stay stale up to **five minutes** (`revalidate = 300`).
- Feedback: reply in the existing group chat / email thread used to share this link (no new accounts or forms in this pass).

## Rollback

Prior production deployment (rollback target):

- ID: `dpl_91gzAmhbfxACNGHBRF6bGcfZUsUc`
- URL: https://booklens-h9ac45rg0-coy44.vercel.app

```bash
cd apps/web
npx vercel rollback dpl_91gzAmhbfxACNGHBRF6bGcfZUsUc --yes
```

After rollback:

1. Confirm which deployment the production aliases point at.
2. Confirm SSO / public access state (rollback does not automatically restore the previous SSO setting).
3. If public exposure is the problem, re-enable Production SSO:

```bash
# Protect production again (and previews), or choose the prior deploymentType
printf '%s' '{"ssoProtection":{"deploymentType":"all_except_custom_domains"}}' > /tmp/bl-sso.json
npx vercel api "/v9/projects/prj_F09FDIfgyMAA2T4jAxszsig6umBr?teamId=team_RRvmOseR6F70Q2c4vnDuzSG6" -X PATCH --input /tmp/bl-sso.json
```

Do not mutate or reseed Supabase during a normal app rollback.
