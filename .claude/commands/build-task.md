---
description: Build a single LoopCloser task in an isolated worktree and open a PR. Usage: /build-task <task-id>
argument-hint: <task-id>   e.g. T12
---

You are a **build worker** for LoopCloser. Your task id is: **$ARGUMENTS**

## 0. Ground yourself
- Read `AGENTS.md` in full (constitution, non-negotiables, DoD).
- Read `tasks/$ARGUMENTS.md` — your `owned_paths`, `depends_on`, `interfaces_provided/consumed`, `dod`,
  and `exit_condition`.
- Read `docs/CONTRACTS.md` — the frozen seams you must consume (never modify).
- Skim the relevant section(s) of `docs/doc.md` referenced by your task.
- Use Context7 MCP for current library API docs when needed (FastAPI, SQLAlchemy, Vite, TanStack
  Query, Playwright, boto3, etc.).

## 1. Set up the worktree
- If not already in one: create a worktree + branch:
  `git worktree add ../loopcloser-worktrees/$ARGUMENTS -b task/w<wave>-$ARGUMENTS-<slug>` (use the wave
  and a short slug from `tasks/$ARGUMENTS.md`). If the `EnterWorktree` tool exists, use it instead.
- Confirm you are on the right branch in the right directory before editing.

## 2. Implement
- Write code **only** within your task's `owned_paths`. If you find you need to touch anything else —
  a seam, `pyproject.toml`, `package.json`, another module — **STOP** and escalate (§5). Do not
  improvise across boundaries.
- Consume the interfaces named in `interfaces_consumed` exactly as defined in `docs/CONTRACTS.md`.
- Provide the interfaces named in `interfaces_provided`.
- Follow the coding conventions in `AGENTS.md` §6 (ruff, mypy --strict, Pydantic v2, tsc strict,
  temperature 0, canonical citation shape).
- Honor the non-negotiables that apply to your module (e.g. LLM never overrides a validator;
  synthetic-only; never log secrets or full document text).

## 3. Test
- Write the unit/integration tests required by your task's `dod`.
- The deterministic core must be testable **without an LLM** (use `stub`/fixtures).
- Anything touching inference runs in `replay` mode against committed cassettes.

## 4. Self-verify (must be green before a PR)
Run, in your worktree:
```
make verify              # lint + typecheck + test + eval + privacy + ownership (replay mode)
make ownership TASK=$ARGUMENTS   # diff must stay within owned_paths
make privacy
```
Loop until all pass. If `eval` isn't wired for your wave yet, run the subset your task defines.

## 5. Open the PR
- Commit with a clear message ending in the co-author trailer required by the repo.
- Push the branch; open a PR with `gh pr create`:
  - Title: `$ARGUMENTS: <summary>`
  - Body: fill `.github/pull_request_template.md` — DoD checklist ticked, owned-paths attestation,
    pasted `make verify` summary, privacy pass, cassettes-updated Y/N, trace/screenshot if agent/UI.
  - Labels: `wave:<n>`, `task:$ARGUMENTS`.
  - Base: `main`.
- **Do not merge.** A human merges.
- Clean up: `git worktree remove` (or `ExitWorktree`) once the PR is open.

## 5b. Escalation (if blocked)
If you are blocked, need a seam/shared-file change, need a new dependency, or the task is
under-specified: **stop, do not cross ownership boundaries.** Write the blocker clearly (in the PR body
if one exists, otherwise report back to the orchestrator) so a human can resolve it as a separate
integration task.

## Definition of Done (AGENTS.md §11)
Behavior matches `exit_condition`; tests green; `make verify` green in replay; diff within
`owned_paths`; privacy clean; citations resolve; PR opened with template + labels.
