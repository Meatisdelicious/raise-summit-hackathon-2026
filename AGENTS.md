# AGENTS.md — LoopCloser build constitution

**Read this file first, in full, before touching anything.** It governs every AI build-agent working
in this repository. The canonical *product* spec is [`docs/doc.md`](docs/doc.md); the frozen
*interfaces* are [`docs/CONTRACTS.md`](docs/CONTRACTS.md); the task graph is [`docs/TASKS.md`](docs/TASKS.md)
with per-task specs under [`tasks/`](tasks/).

> We are building **LoopCloser** — a document-grounded healthcare-operations agent for the RAISE
> Summit Hackathon 2026, "Statement Two — Vultr enterprise agent" track. It turns explicit,
> clinician-authored follow-up instructions into tracked, auditable obligations. It does **not**
> practice medicine.

---

## 1. Non-negotiables (hard blockers — violating any of these fails the task)

1. **Synthetic data only.** No real PDF, patient identifier, clinician name, organization, logo,
   dossier number, or original-report metadata may ever enter the repo, Vultr, a prompt, a log, a
   screenshot, or the demo. Real material lives only under `data/private/` (git-ignored; must be empty
   in the public tree). Run `make privacy` before every commit.
2. **Vultr Serverless Inference stays on the live critical path.** Planning, extraction, query
   generation, and cited explanation call Vultr live in the deployed demo. The replay adapter exists
   only for CI and tests — never hardcode a decision to fake the live path.
3. **False-closure rate = 0.** The LLM may *propose* an evidence match; it can **never** override a
   failed deterministic validator. When evidence is missing, conflicting, or below threshold, the
   state is `AMBIGUOUS_REQUIRES_REVIEW` — never a closed loop. A false closure is the worst possible
   defect.
4. **No medical advice.** Track only *explicit clinician-authored* instructions. Never diagnose,
   interpret a lab value, apply a clinical guideline autonomously, produce a clinical-risk score, or
   recommend/prescribe treatment. Every external action requires human approval.
5. **Never invent a state or a tool.** The decision state machine has exactly six states and the tool
   registry has exactly eight tools (see §9). Adding to either is out of scope.

## 2. Golden rules for build-agents

- **Edit only the `owned_paths` declared in your task's `tasks/<id>.md`.** Touching any path outside
  them — especially a shared/seam file — is a protocol violation. Stop and escalate (§11).
- `make verify` must pass (in `replay` inference mode) **before** you open a PR.
- `make privacy` must pass before every commit.
- Never commit secrets or anything under `data/private/`.
- Consume the frozen interfaces in `docs/CONTRACTS.md`; **never modify a seam** (§5).
- Humans merge PRs. **Agents never merge.**

## 3. Stack

- **Backend:** Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 (typed) + Alembic · PostgreSQL ·
  `boto3`/S3 client for Vultr Object Storage · PyMuPDF/pypdf · pytest. Package `loopcloser` under
  `apps/api/`.
- **Frontend:** React + TypeScript + Vite · TanStack Query (all server state) · Server-Sent Events
  (live agent trace) · Playwright (demo-path e2e). Under `apps/web/`.
- **Inference:** Vultr Serverless Inference (OpenAI-compatible), temperature 0 for
  extraction/planning. Streamlit is banned.

## 4. Repo map & module-ownership table

Each directory has exactly one owning subagent. Do not write outside your task's `owned_paths`.

| Path | Owner subagent | Responsibility |
|---|---|---|
| `apps/api/src/loopcloser/models/**` | `backend-core` | SQLAlchemy models, Pydantic schemas, enums |
| `apps/api/src/loopcloser/alembic/**` | `backend-core` | the single initial migration |
| `apps/api/src/loopcloser/policies/**` | `backend-core` | validators, decision policy |
| `apps/api/src/loopcloser/agent/decision.py` | `backend-core` | decision state machine |
| `apps/api/src/loopcloser/tools/**` | `backend-core` | the 8-tool registry |
| `apps/api/src/loopcloser/api/**` | `backend-core` | FastAPI routes |
| `apps/api/src/loopcloser/agent/** (except decision.py)` | `agent-orchestration` | orchestrator, planning, inference adapter |
| `apps/api/tests/cassettes/**` | `agent-orchestration` | recorded Vultr cassettes |
| `apps/api/src/loopcloser/retrieval/**`, `storage/**` | `retrieval-data` | retrieval + object storage |
| `scripts/generate_synthetic_data.py`, `data/**`, `scripts/eval.py` | `retrieval-data` | synthetic corpus + eval |
| `apps/web/**` | `frontend` | the case workbench UI + Playwright |
| `infra/**`, `.github/**`, deploy/seed/reset/demo scripts | `devops-qa` | deploy, QA, demo hardening |

Shared/seam files (below) are created in **Wave 0 only** and are frozen thereafter.

## 5. Integration seams (frozen — do not change without an orchestrator-owned integration task)

Everyone imports these; changing one breaks parallel work:

- `apps/api/src/loopcloser/models/schemas.py` — Pydantic contracts (`Recommendation`, `Candidate`,
  `Decision`, `ToolCall`, event payloads).
- `apps/api/src/loopcloser/models/enums.py` — the 6-state `DecisionState`, document/candidate types.
- `apps/api/src/loopcloser/tools/base.py` — the `Tool` protocol + registry.
- `apps/api/src/loopcloser/agent/inference/base.py` — the `InferenceClient` protocol.
- FastAPI route stubs in `apps/api/src/loopcloser/api/` and the OpenAPI contract.
- `apps/web/src/types/` — the TS mirror of the schemas.

If you genuinely need a seam change or a new dependency: **stop and escalate** (§11). Do not edit the
shared file inline.

## 6. Coding conventions

- **Python:** `ruff` (lint+format) clean; `mypy --strict` clean; Pydantic v2; async FastAPI;
  SQLAlchemy 2.0 typed `Mapped[...]`; no bare `except`; no `print` in library code (use logging).
- **TypeScript:** `tsc --noEmit` clean under `strict: true`; no `any`; TanStack Query for all server
  state; SSE for the live trace; accessible components (keyboard, labels, contrast, no color-only
  status).
- **Citations** are always `{document_id, page_number, start_offset, end_offset}` and must resolve to
  a real page. Temperature is 0 for extraction/planning. Never log full document text or secrets.

## 7. Inference modes

Selected by env `LOOPCLOSER_INFERENCE_MODE`:

- `live` — `VultrInferenceClient`, real Vultr calls. **Used by the deployed demo.**
- `replay` — `ReplayInferenceClient`, returns committed cassettes keyed by request hash.
  **Used by CI, `make test`, `make eval`.** Deterministic (fixed corpus + temperature 0).
- `stub` — `StubInferenceClient`, canned outputs for pure unit tests.
- Cassettes are refreshed **from real Vultr** via `make record` (needs credentials, task T32) so CI
  validates the same behavior the live demo produces.

## 8. Running the harness

```
make install     # deps (uv sync + npm ci)
make verify      # THE PRE-PR GATE = lint + typecheck + test + eval + privacy + ownership (replay mode)
make test        # pytest (replay)
make eval        # scripts/eval.py — enforces release gates (replay)
make e2e         # Playwright (replay)
make privacy     # scripts/privacy_scan.py + gitleaks
make ownership TASK=<id>   # scripts/check_ownership.py — diff must stay within owned_paths
make record      # refresh cassettes from live Vultr (needs creds)
make demo        # run backend in live mode against Vultr
make reset       # scripts/reset_demo.py
```

## 9. Canonical constants (copy verbatim — never invent variants)

**Decision states (exactly six):**
`COMPLETED`, `SCHEDULED_NOT_COMPLETED`, `OPEN_NOT_DUE`, `OPEN_OVERDUE`,
`AMBIGUOUS_REQUIRES_REVIEW`, `CLOSED_BY_DOCUMENTED_EXCEPTION`.

**Tools (exactly eight):**
`search_documents`, `get_document_context`, `resolve_deadline`, `normalize_target`,
`validate_completion`, `create_task_draft`, `approve_task`, `schedule_monitor`.

**Demo cases:** A–H with expected states per `docs/doc.md` §12.3 and `data/manifests/ground_truth.json`.

**Agent limits:** ≤12 steps per run; ≤2 retrieval retries per evidence class; invalid model output
retried once with the validation error; exceeding limits ends in `AMBIGUOUS_REQUIRES_REVIEW`.

## 10. Git / worktree / PR conventions

- Branch: `task/w<wave>-<id>-<slug>` (e.g. `task/w1-t12-deterministic-core`).
- Worktree: sibling dir `../loopcloser-worktrees/<id>/` (outside the main tree).
- One agent per worktree per task.
- PR: use `.github/pull_request_template.md`; title `T<id>: <summary>`; apply labels `wave:<n>` and
  `task:<id>`; body includes `Closes` reference to the task and the pasted `make verify` summary.
- **Humans merge; agents never merge.**

## 11. Definition of Done (per task)

A task is Done only when **all** are true:

- [ ] Behavior matches the task's `exit_condition` and `docs/doc.md`.
- [ ] Module unit/integration tests written and green.
- [ ] `make verify` green in `replay` mode.
- [ ] The diff touches **only** the task's `owned_paths` (`make ownership TASK=<id>` passes).
- [ ] `make privacy` clean; no secrets; `data/private/` untouched.
- [ ] Any citations produced resolve to the expected page.
- [ ] PR opened with the template + `wave:*`/`task:*` labels.

## 12. Escalation protocol

If you are blocked, need a seam/shared-file change, need a new dependency, or find the task
under-specified: **stop. Do not improvise across ownership boundaries.** Write the blocker into your
PR body (or, if no PR yet, leave the worktree and report to the orchestrator) and let the human /
orchestrator resolve it as a separate integration task.
