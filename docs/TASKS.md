# TASKS.md — the build task graph (DAG index)

Human-readable mirror of the per-task specs in [`tasks/`](../tasks/). The orchestrator reads the
`tasks/*.md` frontmatter; this file is for humans. Waves run in order; tasks within a wave run in
parallel because their `owned_paths` are disjoint.

**Legend:** owner subagent in `[brackets]`. A task is *ready* when all `depends_on` PRs are merged.

## Wave 0 — Foundation & privacy gate (SEQUENTIAL · 1 agent · blocks everything)
| Task | Title | Deps | Owner |
|---|---|---|---|
| **T00** | Repo scaffold + all deps + Makefile + CI skeleton + `.claude/**` + empty pkg skeleton | — | devops-qa |
| **T01** | Freeze seams: enums, schemas, tool base, inference base + Stub, route stubs, TS types | T00 | backend-core |
| **T02** | Privacy gate: `privacy_scan.py`, ignore patterns, gitleaks, CI privacy job (**Phase 0 exit**) | T00 | devops-qa |

## Wave 1 — Independent leaves (PARALLEL · 4–5 agents)
| Task | Title | Deps | Owner |
|---|---|---|---|
| **T10** | Synthetic data generator + templates + `data/synthetic/` + manifest (cases A–H) | T01 | retrieval-data |
| **T11** | DB models + single Alembic migration + session/engine | T01 | backend-core |
| **T12** | Deterministic validators + decision state machine + unit tests (**no LLM**) | T01 | backend-core |
| **T13** | Frontend shell + routing + TanStack + mock API client (vs contract) | T01 | frontend |
| **T14** | Inference adapter (Vultr live / Replay / Recording + mode switch) | T01 | agent-orchestration |

## Wave 2 — Composition (PARALLEL · 4 agents)
| Task | Title | Deps | Owner |
|---|---|---|---|
| **T20** | Retrieval (filtered + semantic + alias) + object storage + ingestion | T10, T11 | retrieval-data |
| **T21** | 8-tool registry over models + validators + retrieval interface | T11, T12 | backend-core |
| **T22** | `scripts/eval.py` release-gate runner + eval fixtures | T10, T12 | retrieval-data |
| **T23** | Frontend features: inbox, workbench, timeline, evidence/action panels, SSE consumer (vs mock) | T13 | frontend |

## Wave 3 — Orchestration & API (PARALLEL · 3 agents)
| Task | Title | Deps | Owner |
|---|---|---|---|
| **T30** | Agent orchestrator: plan→hunt(≥2)→validate→decide→act, limits, branching, audit, SSE emit | T12, T14, T20, T21 | agent-orchestration |
| **T31** | API endpoints: cases, runs, SSE `/events`, recommendations, task actions, demo/reset, health/ready | T11, T21, T30(iface) | backend-core |
| **T32** | Record cassettes from live Vultr for A–H (**needs creds · human-supervised**) | T30, T31 | agent-orchestration |

## Wave 4 — Integration & deploy (PARALLEL · 3 agents)
| Task | Title | Deps | Owner |
|---|---|---|---|
| **T40** | Wire web → real API + SSE + citation preview + approval flow | T31, T23 | frontend |
| **T41** | Playwright demo-path e2e + `seed_demo.py` / `reset_demo.py` | T31 | devops-qa |
| **T42** | `infra/docker` + `infra/terraform` + Vultr deploy + health checks | T31 | devops-qa |

## Wave 5 — Demo hardening (2 agents · partly sequential)
| Task | Title | Deps | Owner |
|---|---|---|---|
| **T50** | 5-consecutive-run script + latency + recorded-run fallback + dataset freeze | T40, T41, T42, T32 | devops-qa |
| **T51** | Full eval/release gates + README + demo-script + submission evidence | all | agent-orchestration |

**Critical path:** T00 → T01 → T11 → T20 → T30 → T31 → T40 → T50.

**Parallel width per wave:** W0=1, W1=5, W2=4, W3=3, W4=3, W5=2. The orchestrator caps concurrent
worktree workers (default 4; see `.claude/commands/orchestrate.md`).
