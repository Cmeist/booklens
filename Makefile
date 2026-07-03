.PHONY: check-env pipeline-demo pipeline-openlibrary collect-openlibrary seed-supabase web-dev web-build verify status

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

collect-openlibrary:
	uv run python scripts/collect_openlibrary.py \
		$(if $(CONTACT),--contact "$(CONTACT)",) \
		--subjects "$(SUBJECTS)" \
		--limit-per-subject $(LIMIT_PER_SUBJECT) \
		--limit-total $(LIMIT_TOTAL) \
		--sleep-seconds 0.25 \
		--out data/raw/openlibrary_books.csv

seed-supabase:
	uv run python scripts/seed_supabase.py $(if $(SOURCE),--source $(SOURCE),)

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build

verify: pipeline-demo
	uv run ruff check scripts/
	cd apps/web && npm run lint
	cd apps/web && npm run build

status:
	git status
