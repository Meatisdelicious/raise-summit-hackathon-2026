# AGENTS.md — Cycle Sentinel conventions

Short conventions file for anyone (human or AI) working in this repo. The product spec is
[`docs/doc.md`](docs/doc.md); the PRD is [`docs/PRD.md`](docs/PRD.md); the API contract is
[`docs/CONTRACTS.md`](docs/CONTRACTS.md).

> **Cycle Sentinel** — an ovarian-stimulation monitoring & escalation agent for the **lab biologist and
> PMA clinician** (never the patient). As each serial hormone result arrives, it rebuilds the patient's
> trajectory, runs deterministic calculators, conditionally retrieves the governing protocol/SOP rule
> based on what those computations reveal, and emits a **cited monitoring brief** with an **escalation
> flag** a human validates before anything reaches the clinic.

## Non-negotiables
1. **Synthetic data only.** No real hormone results, patient identifiers, or original PDFs in the repo,
   Vultr, prompts, logs, screenshots, or the demo. Real material lives only under `data/private/`
   (git-ignored). Run `make privacy` before every commit.
2. **Internal triage only — never advises the patient.** The output is professional
   clinical-decision-support for the biologist/clinician; a human validates before anything reaches the
   clinic. No autonomous diagnosis, treatment, or prescription.
3. **Every recommendation is grounded in a cited protocol/SOP article.** The LLM interprets and plans;
   deterministic calculators + rules decide the escalation flag.
4. **Keep it an agent, not RAG.** Preserve (a) trajectory reasoning across the time series,
   (b) computation-driven conditional retrieval, (c) the branching escalation tree. Don't collapse it to
   "value → threshold table → normal/abnormal."

## Stack
- **Backend** (`apps/api`, pkg `cyclesentinel`): Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy +
  pgvector · pytest. Exposes JSON + one SSE trace endpoint.
- **Frontend** (`apps/web`): React + TypeScript (built by Raph). Builds against `docs/CONTRACTS.md`.
- **Inference (Vultr Serverless Inference, EU, temperature 0):** LLM **Kimi K2 Instruct** (`CS_LLM_MODEL`,
  text-only) via `POST /v1/chat/completions`; retriever **Vultron Prime-8B**
  (`CS_RETRIEVER_MODEL=vultr/VultronRetrieverPrime-Qwen3.5-8B`) for **visual document retrieval** over
  protocol/SOP page images. Confirm exact ids via `GET /v1/models`. Do **not** use the one-shot
  `/v1/chat/completions/RAG` endpoint (it would collapse the agent loop). Protocol pages + embeddings in
  Vultr Vector Store, **EU region** (HDS-aligned); pgvector fallback.

## Conventions
- Python: `ruff` + `mypy --strict` clean; Pydantic v2; async FastAPI. Frontend: `tsc` strict, no `any`.
- Citations are `{doc_id, article, page?}` and must resolve to a real protocol/SOP article.
- `make verify` (lint + typecheck + test + privacy, replay mode) before committing.
- Use Context7 MCP for current library docs (FastAPI, SQLAlchemy, React, Vite).
