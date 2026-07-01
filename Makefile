.PHONY: check-env pipeline-demo web-dev web-build status

check-env:
	@echo "Checking tool paths..."
	@which git
	@which node || true
	@which npm || true
	@which python3
	@which uv

pipeline-demo:
	uv run python scripts/run_pipeline.py

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build

status:
	git status
