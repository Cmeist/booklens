.PHONY: check-env pipeline-demo status

check-env:
	@echo "Checking tool paths..."
	@which git
	@which node || true
	@which npm || true
	@which python3
	@which uv

pipeline-demo:
	uv run python scripts/run_pipeline.py

status:
	git status
