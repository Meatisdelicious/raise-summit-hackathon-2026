# Architecture

Full detail in [`docs/doc.md`](doc.md) §8. Summary for build-agents.

```text
Browser (React case workbench, Vite)
  |  HTTP + Server-Sent Events
  v
FastAPI orchestration API  ── on Vultr Compute ──────────────────────────┐
  |                    |                          |                        |
  | plan/extract/      | search/validate/         | persist               | store
  | query/explain      | decide (deterministic)   |                       |
  v                    v                          v                        v
Vultr Serverless    tools/ + policies/        Vultr Managed           Vultr Object
Inference (LIVE)    + retrieval/              PostgreSQL              Storage (private)
(critical path)     (deterministic core)      cases/decisions/audit   synthetic PDFs
```

## Layers (backend package `loopcloser`)
- **`agent/`** — orchestrator (state flow: INGESTED → RECOMMENDATION_DETECTED → PLAN_CREATED →
  EVIDENCE_SEARCH → VALIDATE_CANDIDATE → (TARGETED_RETRIEVAL) → DECIDE → DRAFT_OPERATIONAL_ACTION →
  HUMAN_APPROVAL → MONITOR), plus `agent/inference/` (Vultr/replay/stub) and `agent/decision.py` (the
  6-state machine, owned by backend-core).
- **`tools/`** — the 8-tool registry; args/results validated by Pydantic; model can't call unregistered
  tools.
- **`retrieval/`** — page-aware chunking, document-type + date filters before semantic ranking, exact
  alias match for deterministic targets, resolvable citations.
- **`policies/`** — deterministic validators (temporal, final-vs-draft, appointment-vs-completion,
  alias, deadline) and the decision policy. **The LLM can never override these.**
- **`models/`** — SQLAlchemy ORM + Pydantic schemas + enums (the frozen seams).
- **`storage/`** — S3-compatible client for Vultr Object Storage (private bucket, short-lived signed
  URLs).
- **`api/`** — FastAPI routes incl. the SSE trace stream.

## Determinism boundary
Inference proposes (extraction, plan, queries, tool selection, explanation). Deterministic code
disposes (validation, state assignment). This boundary is what makes false-closure = 0 achievable and
what makes CI reproducible via replay cassettes.
