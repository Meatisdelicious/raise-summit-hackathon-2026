# LoopCloser

**A document-grounded healthcare follow-up agent — RAISE Summit Hackathon 2026 (Vultr enterprise-agent track).**

LoopCloser turns explicit, clinician-authored follow-up instructions ("repeat this test within six
months") into tracked, auditable obligations. It plans where proof of completion should exist,
retrieves evidence by class more than once, validates candidates with deterministic tools, assigns one
of six constrained operational states, and drafts the next staff action — every conclusion cited to a
document page, every external action gated on human approval. **It does not practice medicine.**

> ⚠️ **Synthetic data only.** This public repo and the hosted demo use fictional, generated documents.
> No real patient data is present. See [`docs/safety.md`](docs/safety.md).

## How this repo is built
LoopCloser is built by collaborating AI agents (Claude Code) working in isolated git worktrees, each
opening a PR a human merges. The build is driven by a `/loop` orchestrator over a dependency-ordered
task graph.

```
/privacy-gate                 # Phase 0 hard gate — must pass first
/loop /orchestrate            # lead: computes the next wave, spawns parallel worktree workers → PRs
                              # you merge the green PRs; the loop re-plans the next wave
```

### Read these
| Doc | Purpose |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Build constitution — non-negotiables, ownership, DoD. **Read first.** |
| [`docs/doc.md`](docs/doc.md) | Canonical product & implementation spec (27 sections) |
| [`docs/PRD.md`](docs/PRD.md) | Condensed product brief |
| [`docs/CONTRACTS.md`](docs/CONTRACTS.md) | Frozen interfaces every module imports |
| [`docs/TASKS.md`](docs/TASKS.md) + [`tasks/`](tasks/) | The wave/dependency task graph |
| [`docs/WORKTREES.md`](docs/WORKTREES.md) | Worktree + PR protocol |
| [`docs/architecture.md`](docs/architecture.md) | System architecture on Vultr |
| [`docs/demo-script.md`](docs/demo-script.md) | The two-minute demo |

## Stack
Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy + Alembic · PostgreSQL · React + TS + Vite + TanStack
Query + SSE · Playwright · pytest · **Vultr** Serverless Inference + Object Storage + Managed
PostgreSQL + Compute.

## Quick start (once the build has produced code)
```
cp .env.example .env      # fill for live mode; replay mode needs no secrets
make install
make db-up migrate seed
make verify               # lint + typecheck + test + eval + privacy + ownership (replay mode)
make demo                 # run in live mode against Vultr
```

## The five hard rules
1. Synthetic data only. 2. Vultr on the live critical path. 3. False-closure = 0. 4. No medical advice.
5. Never invent a state (6) or a tool (8). Full text in [`AGENTS.md`](AGENTS.md).
