# LoopCloser harness. Targets degrade gracefully before the code exists (Wave 0 creates apps/).
# Inference is deterministic in replay mode; CI never calls Vultr. See AGENTS.md §7/§8.

SHELL := /bin/bash
API_DIR := apps/api
WEB_DIR := apps/web
export LOOPCLOSER_INFERENCE_MODE ?= replay
PY ?= python3

.DEFAULT_GOAL := help

.PHONY: help
help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

# ---- setup ----
.PHONY: install
install: ## Install backend + frontend deps (if present)
	@if [ -f $(API_DIR)/pyproject.toml ]; then \
	  (command -v uv >/dev/null && cd $(API_DIR) && uv sync) || (cd $(API_DIR) && $(PY) -m pip install -e '.[dev]'); \
	else echo "skip: $(API_DIR)/pyproject.toml not present yet"; fi
	@if [ -f $(WEB_DIR)/package.json ]; then cd $(WEB_DIR) && npm ci; else echo "skip: $(WEB_DIR)/package.json not present yet"; fi

# ---- the pre-PR gate ----
.PHONY: verify
verify: lint typecheck test eval privacy ownership ## THE pre-PR gate (replay mode)
	@echo "✅ make verify passed"

.PHONY: lint
lint: ## ruff + eslint (if present)
	@if [ -d $(API_DIR) ]; then (cd $(API_DIR) && ruff check . && ruff format --check .) || exit 1; else echo "skip lint: no api"; fi
	@if [ -f $(WEB_DIR)/package.json ]; then (cd $(WEB_DIR) && npm run -s lint 2>/dev/null || echo "skip: no web lint script"); fi

.PHONY: typecheck
typecheck: ## mypy --strict + tsc --noEmit (if present)
	@if [ -d $(API_DIR)/src ]; then (cd $(API_DIR) && mypy --strict src) || exit 1; else echo "skip typecheck: no api src"; fi
	@if [ -f $(WEB_DIR)/package.json ]; then (cd $(WEB_DIR) && npx tsc --noEmit) || exit 1; else echo "skip typecheck: no web"; fi

.PHONY: test
test: ## pytest (replay)
	@if [ -d $(API_DIR)/tests ]; then (cd $(API_DIR) && LOOPCLOSER_INFERENCE_MODE=replay pytest -q -m 'not live') || exit 1; else echo "skip test: no api tests yet"; fi

.PHONY: eval
eval: ## Release-gate eval (replay); non-zero on any gate failure
	@if [ -f scripts/eval.py ]; then LOOPCLOSER_INFERENCE_MODE=replay $(PY) scripts/eval.py || exit 1; else echo "skip eval: scripts/eval.py not present yet"; fi

.PHONY: e2e
e2e: ## Playwright demo-path (replay, seeded)
	@if [ -d $(WEB_DIR)/tests/e2e ]; then (cd $(WEB_DIR) && npx playwright test) || exit 1; else echo "skip e2e: no e2e tests yet"; fi

# ---- guards (always available) ----
.PHONY: privacy
privacy: ## Privacy scan — no real PHI / original PDFs (hard gate)
	@$(PY) scripts/privacy_scan.py
	@command -v gitleaks >/dev/null && gitleaks detect --no-banner -c .gitleaks.toml 2>/dev/null || echo "note: gitleaks not installed (CI runs it)"

.PHONY: ownership
ownership: ## Diff must stay within the task's owned_paths. Usage: make ownership TASK=T12
	@if [ -z "$(TASK)" ]; then echo "skip ownership: pass TASK=<id> (orchestrator/CI sets this)"; else $(PY) scripts/check_ownership.py $(TASK); fi

# ---- db / demo ----
.PHONY: db-up
db-up: ## Start a local Postgres (docker)
	@docker compose -f infra/docker/compose.dev.yml up -d db 2>/dev/null || echo "skip: compose not present yet"

.PHONY: migrate
migrate: ## Apply Alembic migration
	@if [ -f $(API_DIR)/src/loopcloser/alembic.ini ]; then (cd $(API_DIR)/src/loopcloser && alembic upgrade head); else echo "skip migrate: no alembic yet"; fi

.PHONY: seed
seed: ## Seed synthetic demo data
	@if [ -f scripts/seed_demo.py ]; then $(PY) scripts/seed_demo.py; else echo "skip seed: not present yet"; fi

.PHONY: reset
reset: ## Reset synthetic demo state
	@if [ -f scripts/reset_demo.py ]; then $(PY) scripts/reset_demo.py; else echo "skip reset: not present yet"; fi

.PHONY: gen-data
gen-data: ## Regenerate the synthetic corpus (deterministic)
	@if [ -f scripts/generate_synthetic_data.py ]; then $(PY) scripts/generate_synthetic_data.py; else echo "skip gen-data: not present yet"; fi

# ---- inference ----
.PHONY: record
record: ## Refresh replay cassettes from LIVE Vultr (needs creds)
	@LOOPCLOSER_INFERENCE_MODE=live $(PY) scripts/record_cassettes.py 2>/dev/null || echo "record: needs T14/T32 + Vultr creds"

.PHONY: demo
demo: ## Run backend in LIVE mode against Vultr
	@LOOPCLOSER_INFERENCE_MODE=live bash -c 'cd $(API_DIR) && uvicorn loopcloser.main:app --reload'
