# Architecture

```text
React case view (apps/web, Raph)
  │  REST (JSON)  +  SSE (live agent trace)
  ▼
FastAPI agent (apps/api, pkg cyclesentinel) ── on Vultr Compute ─────────────────┐
  │ plan / interpret / write brief        │ deterministic calculators           │
  ▼                                        ▼                                     ▼
Vultr LLM: Kimi K2 Instruct (LIVE)    compute_* + rules (no LLM)          Vultr PostgreSQL (EU)
  planning, interpretation,           E2 rate, E2/follicle, OHSS          patients · results · briefs · agent_runs
  brief prose, tool selection         composite, P4-for-day, timing
       ▲   (text-only → reads the retrieved page's TEXT LAYER)
       │ retrieve_protocol_rule(rule_type=…)  ← conditional, computation-driven
       ▼
Vultr Retriever: Vultron Prime-8B (Visual Document Retrieval)
  embeds protocol/SOP PAGE IMAGES + query → top-k pages (score + text layer + article)
       ▼
Vultr Vector Store (EU)  [pgvector fallback]        (+ Vultr Object Storage: synthetic source pages)
  page embeddings · retrieval-only mode
```

## Layers (`cyclesentinel`)
- **`agent/`** — the orchestration loop (plan → retrieve context → retrieve trajectory → compute → branch
  → conditional retrieve → compute action → decide → draft → escalate), step/limit handling, run + step
  logging, SSE event emission. Plus `agent/inference/` — a Vultr client for **both** the LLM
  (Kimi K2, `POST /v1/chat/completions`) and the **Prime-8B** visual retriever — with `live` / `replay`
  / `stub` modes selected by `CS_INFERENCE_MODE`.
- **`calculators/`** — the deterministic signal functions (pure, unit-tested). **The LLM never overrides these.**
- **`retrieval/`** — `retrieve_protocol_rule`: **visual document retrieval** via Vultron **Prime-8B**
  over the page-indexed corpus, filtered by `rule_type`; returns top-k **pages** (score + text layer +
  `{doc_id, page, article}` citation). Backed by Vultr Vector Store (EU); pgvector is the fallback.
  Called explicitly per branch — **not** the one-shot Vultr RAG endpoint.
- **`tools/`** — the tool registry wrapping calculators + retrieval + brief/escalation, Pydantic-validated.
- **`models/`** — SQLAlchemy ORM + Pydantic schemas + the state enum (the shapes in `CONTRACTS.md`).
- **`api/`** — FastAPI routes incl. the SSE trace stream.

## Determinism boundary
Inference **proposes** (plan, interpretation, which rule to fetch, brief prose). Deterministic code
**disposes** (the computed signals and the escalation flag). This is what keeps it safe (no autonomous
clinical verdict), auditable (every flag traces to a calculator + a cited article), and reproducible
(replay cassettes make CI deterministic while the demo runs live on Vultr).
