.PHONY: help check-env pipeline-demo pipeline-live web-install web-dev web-build clean-data

help:
	@echo "BookLens commands"
	@echo "  make check-env                  Verify WSL/Linux tool paths"
	@echo "  make pipeline-demo              Run offline data pipeline demo"
	@echo "  make pipeline-live CONTACT=...  Run small live Open Library collection"
	@echo "  make web-install                Install Next.js app dependencies"
	@echo "  make web-dev                    Start Next.js dev server"
	@echo "  make web-build                  Build Next.js app"
	@echo "  make clean-data                 Remove generated raw/processed data"

check-env:
	@echo "Repo: $$(pwd)"
	@echo "node: $$(which node || true)"
	@echo "npm: $$(which npm || true)"
	@echo "python: $$(which python || true)"
	@echo "uv: $$(which uv || true)"
	@echo "git: $$(which git || true)"
	@echo "make: $$(which make || true)"
	@if pwd | grep -q '^/mnt/c/'; then echo "WARNING: repo is under /mnt/c. Move it to ~/dev/booklens for WSL development."; fi
	@if which node 2>/dev/null | grep -q '^/mnt/c/'; then echo "WARNING: Windows node is on PATH. Use Linux node via nvm inside WSL."; fi
	@if which npm 2>/dev/null | grep -q '^/mnt/c/'; then echo "WARNING: Windows npm is on PATH. Use Linux npm via nvm inside WSL."; fi
	@if which python 2>/dev/null | grep -q '^/mnt/c/'; then echo "WARNING: Windows python is on PATH. Use Linux Python/uv inside WSL."; fi

pipeline-demo:
	uv run python run_pipeline.py --mode demo

pipeline-live:
	@if [ -z "$(CONTACT)" ]; then echo "Usage: make pipeline-live CONTACT=you@example.com"; exit 1; fi
	uv run python run_pipeline.py --mode live --contact $(CONTACT) --limit-per-subject 25

web-install:
	cd apps/web && npm install

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build

clean-data:
	rm -f data/raw/*.csv data/processed/*.csv data/processed/*.txt
