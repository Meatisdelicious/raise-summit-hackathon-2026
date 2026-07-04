# CLAUDE.md

This repo builds **LoopCloser**, a document-grounded healthcare follow-up agent for the RAISE Summit
Hackathon 2026 (Vultr enterprise-agent track). Development is driven by collaborating AI worktree
agents that each open a PR a human merges.

## Read these first
- **[`AGENTS.md`](AGENTS.md)** — the build constitution. Non-negotiables, ownership boundaries, DoD.
  **Every agent reads this in full before acting.**
- **[`docs/doc.md`](docs/doc.md)** — the canonical product & implementation spec (27 sections).
- **[`docs/CONTRACTS.md`](docs/CONTRACTS.md)** — the frozen interfaces every module imports.
- **[`docs/TASKS.md`](docs/TASKS.md)** + **[`tasks/`](tasks/)** — the wave/dependency task graph.
- **[`docs/WORKTREES.md`](docs/WORKTREES.md)** — the worktree + PR protocol.

## The five hard rules (full text in AGENTS.md §1)
1. Synthetic data only — no real PHI anywhere, ever.
2. Vultr Serverless Inference stays on the live critical path.
3. False-closure = 0 — the LLM never overrides a deterministic validator.
4. No medical advice — explicit clinician instructions only; human approval for external actions.
5. Never invent a state (6) or a tool (8).

## Harness commands
`make verify` is the pre-PR gate (lint + typecheck + test + eval + privacy + ownership, replay mode).
See AGENTS.md §8 for the full list.

## Driving the build
- Lead loop: `/loop /orchestrate` — computes the next unblocked wave and spawns parallel worktree
  workers that each open a PR. You (the human) merge; the loop re-plans.
- Single worker: `/build-task <id>`.
- Privacy gate (must pass before any build): `/privacy-gate`.

## Context7 for library docs
When you need current API/config details for a library (FastAPI, SQLAlchemy, TanStack Query, Vite,
Playwright, boto3, etc.), use the Context7 MCP (`resolve-library-id` → `query-docs`) rather than
relying on memory.
