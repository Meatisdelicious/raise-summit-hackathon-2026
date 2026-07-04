# CLAUDE.md

This repo builds **Cycle Sentinel**, an ovarian-stimulation monitoring & escalation agent for the RAISE
Summit Hackathon 2026 (Vultr enterprise-agent track). Backend = Python/FastAPI (`apps/api`); frontend =
React by teammate Raph (`apps/web`).

## Read these first
- **[`docs/PRD.md`](docs/PRD.md)** — the product brief.
- **[`docs/doc.md`](docs/doc.md)** — the technical spec (agent loop, tools, calculators, states, data).
- **[`docs/CONTRACTS.md`](docs/CONTRACTS.md)** — the API contract (REST + SSE + TS types) Raph builds against.
- **[`AGENTS.md`](AGENTS.md)** — conventions + non-negotiables.
- **[`docs/safety.md`](docs/safety.md)** — the safety/privacy boundary.

## The four hard rules (full text in AGENTS.md)
1. Synthetic data only — no real hormone data / identifiers anywhere.
2. Internal triage only — never advises the patient; a human validates before the clinic.
3. Every recommendation cites a protocol/SOP article.
4. Keep it an agent (trajectory + computation-driven conditional retrieval + branching), not RAG.

## Harness
`make verify` = lint + typecheck + test + privacy (replay mode). `make dev` runs the API. See the Makefile.

## Context7 for library docs
Use the Context7 MCP (`resolve-library-id` → `query-docs`) for current API/config details for FastAPI,
SQLAlchemy/pgvector, React, Vite, etc., rather than relying on memory.
