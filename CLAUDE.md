# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**MILA** is an ovarian-stimulation (IVF) monitoring &
escalation *agent* for a lab biologist — RAISE Summit 2026, Vultr enterprise-agent track. Monorepo:
backend `apps/api` (Python 3.12 / FastAPI, pkg `cyclesentinel`, `src` layout) + frontend `apps/web`
(React 18 / Vite / react-router / recharts). The pitch audience is **non-biologists** — the UI keeps
a plain-language layer over the clinical detail.

## Commands

```bash
make install       # backend deps (uv, Python 3.12) + frontend deps (npm ci)
make verify        # THE pre-commit gate: ruff + ruff format --check + mypy --strict + pytest(replay) + privacy
make stack         # offline demo: backend (replay) + UI  → http://localhost:5173  (no keys)
make demo-stack    # LIVE demo: backend on Vultr + UI     → http://localhost:5173  (sources ./.env)
make dev | demo    # backend only, replay | live (:8000)
make web           # frontend only (:5173); proxies /api to :8000
make seed          # regenerate data/synthetic/** (corpus, cases, thresholds; renders page PNGs via Pillow)
```

- Tools run through `uv run` (via the Makefile `$(RUN)` var) — **no venv activation needed**. Backend deps
  live in the `dev` **extra**, so a bare `uv sync` misses ruff/mypy/pytest — always `uv sync --extra dev`.
- **Single test:** `cd apps/api && CS_INFERENCE_MODE=replay uv run pytest -q tests/agent/test_trajectories.py -k "K and replay"`.
- **Frontend checks:** `cd apps/web && npm run build` (= `tsc --noEmit` + `vite build`). The backend gate
  (`make verify/lint/typecheck/test`) is **API-ONLY** on purpose — never add web `tsc`/eslint back into those
  targets: the backend CI job installs no Node deps and would fail. The frontend has its own `web` CI job.

## Architecture (the parts that span files)

**Agent loop** (`apps/api/src/cyclesentinel/agent/loop.py`, ≤10 steps, emits an `AgentEvent` trace):
`plan → get_patient_context → get_trajectory → compute 6 signals → conditional branch → retrieve_rule →
action → brief → escalate → done`. The **determinism boundary** is the core idea: the LLM *proposes*
(plan, prose, and — via a tripped signal — *which* rule to fetch); deterministic Python *disposes* (the
computed signals in `calculators/`, the escalation flag + state in `agent/state.py`, the citation
grounding in `agent/brief.py`). Fail-safe: anything escalating never resolves to `ROUTINE_CONTINUE`.

**Not-RAG invariant (guarded by tests):** retrieval is reachable *only* through `agent/branch.py`
(`branches_for(signals) → rule_type[]`). The routine patient (`pat-R`) must emit **zero** `branch` /
`retrieve_rule` events. Never wire retrieval as a fixed pipeline step.

**Tools & calculators:** `tools/` is an 11-tool registry (Pydantic-validated; the model may not call an
unregistered tool). There are **6 calculators but only 5 `compute_*` tools** — `response_curve` runs in
the compute phase as a `ComputedSignal`, it is *not* a 12th tool.

**Inference modes seam** (`inference/`, one interface, agent is mode-agnostic): `live` (Vultr), `replay`
(content-hashed cassettes under `apps/api/tests/cassettes/<CASE>/`), `stub` (canned). Selected by
`CS_INFERENCE_MODE`. CI/tests never hit the network.

**The frozen contract:** `docs/CONTRACTS.md` ⇄ `apps/api/src/cyclesentinel/{enums,schemas,events}.py`
(flat files) ⇄ `apps/web/src/types/contracts.ts`. A test (`tests/contract/`) parses CONTRACTS.md and fails
on drift. Field names must match byte-for-byte across all three.

**Frontend ⇄ backend:** the UI talks to a relative `/api`; `vite.config.ts` proxies it to `:8000` (no
CORS). `apps/web/src/api/index.ts` picks the real client by default; `VITE_USE_MOCKS=true` switches to the
offline mock client. Both implement one `Api` interface, so components never know which is live.

## Vultr live path (verified against the real API)

- **LLM** = `moonshotai/Kimi-K2.6` via `POST /v1/chat/completions` (temperature 0). The plan/brief prompts
  force `response_format: json_object` (live-only; not part of the cassette key).
- **Retrieval** = two stages in `inference/live.py`: Vultr **Vector Store** `search` (dense recall) →
  **Vultron Prime-8B** rerank via `POST /v1/rerank`. Vultron is a *ReRank* model — there is **no
  `/v1/embeddings` endpoint** and the store's `model` param is ignored, so Vultron is only reachable through
  rerank. One collection per `rule_type` (`retrieval/collections.py`: `csohss`/`cslut`/`cspoor`/`csstim`);
  populate them once with `python scripts/index_corpus.py`.

## The four hard rules (full text in [`AGENTS.md`](AGENTS.md))

1. **Synthetic data only** — no real hormone data / identifiers / PDFs (only under `data/synthetic/`).
   Enforced by `scripts/privacy_scan.py` (required CI gate). Real lab PDFs have leaked twice
   (`docs/healthcare_data/`) — treat this gate as non-optional.
2. **Internal triage only** — a human validates every brief; never patient-facing, nothing auto-sent.
3. **Every recommendation cites a protocol/SOP article** — the grounding guard rejects unresolved citations.
4. **Agent, not RAG** — trajectory reasoning + computation-driven conditional retrieval + branching.

## Gotchas (cost time to rediscover)

- **`.env` lives at the REPO ROOT, not `apps/api/`.** pydantic-settings reads `.env` from the cwd, and the
  test suite runs in `apps/api` — an `apps/api/.env` silently overrides offline test defaults (breaks ~18
  tests). `make demo`/`make demo-stack` `source ./.env`.
- **Replay cassettes are keyed by request hash, and the LLM key includes `cs_llm_model`.** Keep the
  `cs_llm_model` *default* empty (what the cassettes were seeded with); live sets the real id in `.env`.
  Changing an LLM prompt (`agent/prompts.py`) changes the keys → re-seed with
  `cd apps/api && uv run python ../../scripts/record_cassettes.py --seed`.
- **DB:** SQLite for tests/dev, Postgres+pgvector only when `DATABASE_URL` points at Postgres (live). The
  vector store is a *separate* abstraction from the relational DB.

## Read first
[`docs/PRD.md`](docs/PRD.md) (product) · [`docs/doc.md`](docs/doc.md) (spec) ·
[`docs/CONTRACTS.md`](docs/CONTRACTS.md) (the frozen seam) · [`docs/safety.md`](docs/safety.md) ·
[`AGENTS.md`](AGENTS.md) (non-negotiables).

## Context7 for library docs
Use the Context7 MCP (`resolve-library-id` → `query-docs`) for current API/config details (FastAPI,
SQLAlchemy/pgvector, React, Vite, recharts) rather than relying on memory.
