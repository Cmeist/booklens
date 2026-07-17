.PHONY: check-env pipeline-demo pipeline-openlibrary collect-openlibrary collect-loc import-loc enrich-openlibrary-ratings enrich-openlibrary-pages enrich-google-books enrich-hosted-ratings import-popularity-signals seed-supabase tag-tests cleanup-hosted-tags web-dev web-build vercel-deploy modal-deploy modal-refresh verify status

check-env:
	@echo "Checking tool paths..."
	@which git
	@which node || true
	@which npm || true
	@which python3
	@which uv

pipeline-demo:
	uv run python scripts/run_pipeline.py

pipeline-openlibrary:
	uv run python scripts/run_pipeline.py --openlibrary

CONTACT ?=
LIMIT_PER_SUBJECT ?= 15
LIMIT_TOTAL ?= 120
SUBJECTS ?= fantasy,science_fiction,romance,mystery,thriller,historical_fiction,young_adult,classics,biography,literary_fiction
NODE_DIR ?= /home/coy/.nvm/versions/node/v20.20.2/bin

collect-openlibrary:
	uv run python scripts/collect_openlibrary.py \
		$(if $(CONTACT),--contact "$(CONTACT)",) \
		--subjects "$(SUBJECTS)" \
		--limit-per-subject $(LIMIT_PER_SUBJECT) \
		--limit-total $(LIMIT_TOTAL) \
		--sleep-seconds 0.25 \
		--out data/raw/openlibrary_books.csv

LOC_SUBJECTS ?= fantasy fiction,science fiction,detective and mystery stories,juvenile fiction,biography
LOC_LIMIT_PER_SUBJECT ?= 20
LOC_LIMIT_TOTAL ?= 100
LOC_DATA_DIR ?= data
LOC_CANDIDATES ?= data/processed/loc/candidates.json
LOC_REPORT_ROOT ?= data/processed/loc

# LoC collection is isolated from run_pipeline.py and never rewrites web fixtures.
collect-loc:
	uv run python scripts/collect_loc_books.py \
		$(if $(CONTACT),--contact "$(CONTACT)",) \
		--subjects "$(LOC_SUBJECTS)" \
		--limit-per-subject $(LOC_LIMIT_PER_SUBJECT) \
		--limit-total $(LOC_LIMIT_TOTAL) \
		--sleep-seconds 4 \
		--out-dir "$(LOC_DATA_DIR)" \
		$(if $(filter 1 true TRUE yes YES,$(RESUME)),--resume,)

# Hosted LoC import/restore is read-only unless APPLY=1 is explicitly supplied.
import-loc:
	uv run python scripts/import_loc_books.py \
		$(if $(RESTORE),--restore "$(RESTORE)",--candidates "$(LOC_CANDIDATES)") \
		--report-root "$(LOC_REPORT_ROOT)" \
		$(if $(filter 1 true TRUE yes YES,$(APPLY)),--apply,)

enrich-openlibrary-ratings:
	uv run python scripts/enrich_openlibrary_ratings.py $(if $(LIMIT),--limit $(LIMIT),)

enrich-openlibrary-pages:
	uv run python scripts/enrich_openlibrary_pages.py $(if $(LIMIT),--limit $(LIMIT),)

enrich-google-books:
	uv run python scripts/enrich_google_books.py $(if $(LIMIT),--limit $(LIMIT),)

# Hosted ratings fill (missing/zero only). Dry-run by default. Pass APPLY=1 to write.
# Smoke: LIMIT=20 make enrich-hosted-ratings
# Apply smoke: LIMIT=20 APPLY=1 CONTACT=you@example.com make enrich-hosted-ratings
enrich-hosted-ratings:
	uv run python scripts/enrich_hosted_ratings.py \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(CONTACT),--contact "$(CONTACT)",) \
		$(if $(filter 1 true TRUE yes YES,$(APPLY)),--apply,) \
		$(if $(filter 1 true TRUE yes YES,$(SKIP_GOOGLE)),--skip-google,)

# Popularity signals (NYT Books API). Smoke: LIMIT=3. Never overwrites core books.*.
# Default is report-only. Pass WRITE_DB=1 only after migration apply + explicit approval.
import-popularity-signals:
	uv run python scripts/import_popularity_signals.py \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(LISTS),--lists "$(LISTS)",) \
		$(if $(FROM_JSON),--from-json "$(FROM_JSON)",) \
		$(if $(filter 1 true TRUE yes YES,$(WRITE_DB)),--write-db,)

seed-supabase:
	uv run python scripts/seed_supabase.py $(if $(SOURCE),--source $(SOURCE),)

tag-tests:
	uv run python -m unittest discover -s tests -p 'test_tag*.py'

# Canonical tag maintenance is dry-run by default. Hosted writes require APPLY=1.
# Audit: make cleanup-hosted-tags
# Apply after explicit approval: APPLY=1 make cleanup-hosted-tags
# Restore preview: RESTORE=data/processed/tag_cleanup/backups/pre-cleanup-... make cleanup-hosted-tags
# Restore after explicit approval: RESTORE=... APPLY=1 make cleanup-hosted-tags
cleanup-hosted-tags:
	uv run python scripts/cleanup_hosted_tags.py \
		$(if $(RESTORE),--restore "$(RESTORE)",) \
		$(if $(filter 1 true TRUE yes YES,$(APPLY)),--apply,)

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build

vercel-deploy:
	cd apps/web && PATH=$(NODE_DIR):$(PATH) npx vercel --prod

modal-deploy:
	uv run modal deploy modal_app.py

modal-refresh:
	uv run modal run modal_app.py --limit-total $(LIMIT_TOTAL) --limit-per-subject $(LIMIT_PER_SUBJECT)

verify: tag-tests pipeline-demo
	uv run ruff check scripts/ tests/
	cd apps/web && npm run lint
	cd apps/web && npm run build

status:
	git status
