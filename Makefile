.PHONY: check-env pipeline-demo pipeline-openlibrary collect-openlibrary enrich-google-books seed-supabase web-dev web-build vercel-deploy modal-deploy modal-refresh verify status

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

enrich-google-books:
	uv run python scripts/enrich_google_books.py $(if $(LIMIT),--limit $(LIMIT),)

seed-supabase:
	uv run python scripts/seed_supabase.py $(if $(SOURCE),--source $(SOURCE),)

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

verify: pipeline-demo
	uv run ruff check scripts/
	cd apps/web && npm run lint
	cd apps/web && npm run build

status:
	git status
