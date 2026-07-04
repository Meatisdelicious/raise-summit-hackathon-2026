# Cycle Sentinel harness. Lean targets. Backend = apps/api (pkg cyclesentinel); frontend = apps/web (Raph).
# Inference is deterministic in replay mode for tests; live mode calls Vultr. See docs/doc.md.

SHELL := /bin/bash
API_DIR := apps/api
WEB_DIR := apps/web
export CS_INFERENCE_MODE ?= replay
PY ?= python3
# Prefer `uv run` so console scripts (uvicorn) resolve without activating the venv.
RUN := $(shell command -v uv >/dev/null 2>&1 && echo 'uv run')

.DEFAULT_GOAL := help

.PHONY: help
help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n",$$1,$$2}'

.PHONY: install
install: ## Install backend + frontend deps (if present)
	@if [ -f $(API_DIR)/pyproject.toml ]; then (command -v uv >/dev/null && cd $(API_DIR) && uv sync --extra dev) || (cd $(API_DIR) && $(PY) -m pip install -e '.[dev]'); else echo "skip: no $(API_DIR)/pyproject.toml yet"; fi
	@if [ -f $(WEB_DIR)/package.json ]; then cd $(WEB_DIR) && npm ci; else echo "skip: no $(WEB_DIR)/package.json yet"; fi

.PHONY: verify
verify: lint typecheck test privacy ## Pre-commit gate
	@echo "✅ verify passed"

# NB: the backend gate (verify/lint/typecheck/test) is API-ONLY. The frontend has its own build
# check (apps/web: `npm run build` = tsc --noEmit + vite build) run by the `web` CI job — keeping
# them separate means the backend CI job needs no Node/web deps.
.PHONY: lint
lint: ## ruff (backend)
	@if [ -d $(API_DIR) ]; then (cd $(API_DIR) && $(RUN) ruff check . && $(RUN) ruff format --check .) || exit 1; else echo "skip lint: no api"; fi

.PHONY: typecheck
typecheck: ## mypy --strict (backend)
	@if [ -d $(API_DIR)/src ]; then (cd $(API_DIR) && $(RUN) mypy --strict src) || exit 1; else echo "skip typecheck: no api src"; fi

.PHONY: test
test: ## pytest (replay mode)
	@if [ -d $(API_DIR)/tests ]; then (cd $(API_DIR) && CS_INFERENCE_MODE=replay $(RUN) pytest -q -m 'not live') || exit 1; else echo "skip test: no api tests yet"; fi

.PHONY: privacy
privacy: ## Privacy scan — no real hormone data / identifiers / PDFs outside data/synthetic/
	@$(PY) scripts/privacy_scan.py
	@command -v gitleaks >/dev/null && gitleaks detect --no-banner -c .gitleaks.toml 2>/dev/null || echo "note: gitleaks not installed (CI runs it)"

.PHONY: seed
seed: ## Generate the synthetic corpus + demo cases (renders real page images via Pillow in the venv)
	@if [ ! -f scripts/generate_synthetic_data.py ]; then echo "skip seed: not present yet"; \
	elif [ -f $(API_DIR)/pyproject.toml ] && command -v uv >/dev/null; then (cd $(API_DIR) && uv run python ../../scripts/generate_synthetic_data.py); \
	else $(PY) scripts/generate_synthetic_data.py; fi

.PHONY: dev
dev: ## Run the backend API (uvicorn) in replay mode
	@cd $(API_DIR) && CS_INFERENCE_MODE=replay $(RUN) uvicorn cyclesentinel.main:app --reload

.PHONY: demo
demo: ## Run the backend in LIVE mode against Vultr (sources ./.env — kept out of apps/api so tests ignore it)
	@set -a; [ -f .env ] && . ./.env; set +a; cd $(API_DIR) && CS_INFERENCE_MODE=live $(RUN) uvicorn cyclesentinel.main:app --reload

.PHONY: web
web: ## Run the frontend dev server (connects to the backend via the Vite /api proxy)
	@cd $(WEB_DIR) && npm run dev

.PHONY: stack
stack: ## Run backend (replay, offline) + frontend together (Ctrl-C stops both)
	@echo "API  → http://localhost:8000 (replay)   ·   Web → http://localhost:5173"; \
	( cd $(API_DIR) && CS_INFERENCE_MODE=replay $(RUN) uvicorn cyclesentinel.main:app ) & \
	API_PID=$$!; trap "kill $$API_PID 2>/dev/null" EXIT INT TERM; \
	cd $(WEB_DIR) && npm run dev

.PHONY: demo-stack
demo-stack: ## THE LIVE DEMO — backend LIVE on Vultr + frontend together (sources ./.env; Ctrl-C stops both)
	@if [ ! -f .env ]; then echo "error: create ./.env from .env.example with your VULTR_INFERENCE_API_KEY"; exit 1; fi; \
	echo "API  → http://localhost:8000 (LIVE · Vultr)   ·   Web → http://localhost:5173"; \
	set -a; . ./.env; set +a; \
	( cd $(API_DIR) && CS_INFERENCE_MODE=live $(RUN) uvicorn cyclesentinel.main:app ) & \
	API_PID=$$!; trap "kill $$API_PID 2>/dev/null" EXIT INT TERM; \
	cd $(WEB_DIR) && npm run dev
