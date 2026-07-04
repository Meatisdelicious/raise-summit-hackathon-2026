# Architecture

```text
React case view (apps/web, Raph)
  │  REST (JSON)  +  SSE (live agent trace)
  ▼
FastAPI agent (apps/api, pkg cyclesentinel) ── on Vultr Compute ─────────────────┐
  │ plan / interpret / write brief        │ deterministic calculators           │
  ▼                                        ▼                                     ▼
Vultr Serverless Inference (LIVE)     compute_* + rules (no LLM)          Vultr PostgreSQL + pgvector
  planning, interpretation,           E2 rate, E2/follicle, OHSS          (EU region, HDS-aligned)
  brief prose, tool selection         composite, P4-for-day, timing       patients · results · briefs ·
       ▲                                                                   agent_runs · PROTOCOL/SOP corpus
       │ retrieve_protocol_rule(rule_type=…)  ← conditional, computation-driven
       └───────────────────────────────────────────────────────────────► vector search over the corpus
                                                                          (+ Vultr Object Storage: source docs)
```

## Layers (`cyclesentinel`)
- **`agent/`** — the orchestration loop (plan → retrieve context → retrieve trajectory → compute → branch
  → conditional retrieve → compute action → decide → draft → escalate), step/limit handling, run + step
  logging, SSE event emission. Plus `agent/inference/` (Vultr / replay / stub, selected by `CS_INFERENCE_MODE`).
- **`calculators/`** — the deterministic signal functions (pure, unit-tested). **The LLM never overrides these.**
- **`retrieval/`** — `retrieve_protocol_rule` over the pgvector corpus, filtered by `rule_type`; returns
  text + article citation.
- **`tools/`** — the tool registry wrapping calculators + retrieval + brief/escalation, Pydantic-validated.
- **`models/`** — SQLAlchemy ORM + Pydantic schemas + the state enum (the shapes in `CONTRACTS.md`).
- **`api/`** — FastAPI routes incl. the SSE trace stream.

## Determinism boundary
Inference **proposes** (plan, interpretation, which rule to fetch, brief prose). Deterministic code
**disposes** (the computed signals and the escalation flag). This is what keeps it safe (no autonomous
clinical verdict), auditable (every flag traces to a calculator + a cited article), and reproducible
(replay cassettes make CI deterministic while the demo runs live on Vultr).
