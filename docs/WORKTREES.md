# WORKTREES.md — worktree + PR protocol

How collaborating build-agents work in parallel without colliding. Enforced by `AGENTS.md`,
`scripts/check_ownership.py`, and CI.

## Model in one sentence
A **lead** (`/orchestrate`) computes the next unblocked wave from the task graph, assigns **disjoint**
tasks in-memory, and spawns one worktree **worker** per task; each worker builds in isolation, runs
`make verify`, and opens a PR; a **human merges**; the next tick re-plans.

## No mutable board (by design)
There is **no** shared board file to co-edit. Task specs under `tasks/<id>.md` are **read-only**.
"Who's done" is *derived* from merged PRs (`task:*` / `wave:*` labels + merge status). Because the
orchestrator hands out disjoint tasks per wave, two agents can never target the same task — claim
collisions are structurally impossible, and no file is ever written by two agents.

## Branch & worktree naming
- Branch: `task/w<wave>-<id>-<slug>` — e.g. `task/w1-t12-deterministic-core`.
- Worktree: `../loopcloser-worktrees/<id>/` (sibling of the repo, outside the main tree).
- Create with `git worktree add ../loopcloser-worktrees/<id> -b task/w<wave>-<id>-<slug>`
  (the harness uses the `EnterWorktree`/`ExitWorktree` tools which do this for you).
- One agent per worktree per task. Remove the worktree after the PR is opened
  (`git worktree remove`), or let the harness auto-clean it.

## Collision avoidance — defense in depth
1. **Wave 0 owns every shared file** (deps, migration, seams, CI). Nothing else edits them.
2. **Disjoint `owned_paths`** — each task edits only its declared globs.
3. **Ownership guard** — `make ownership TASK=<id>` (and a required CI job) fails any diff that
   touches a path outside `owned_paths`.
4. **One initial Alembic migration** — no parallel migration heads.
5. **Front-loaded dependencies** — a genuine new-dep need escalates; it never edits `pyproject.toml`
   or `package.json` inline.

## PR conventions
- Title: `T<id>: <summary>`. Labels: `wave:<n>`, `task:<id>`.
- Body: use `.github/pull_request_template.md` — DoD checklist, owned-paths attestation, pasted
  `make verify` summary, privacy pass, cassettes-updated Y/N, trace/screenshot for agent/UI tasks.
- Base branch: `main`.

## Merge ordering
- **Within a wave:** PRs touch disjoint paths → mergeable in any order once CI is green.
- **Across waves:** strictly by dependency — a wave's PRs are only *opened* after all its dependency
  tasks are merged to `main`.
- **Humans merge. Agents never merge.** (Privacy/safety-critical repo — keep a human in the loop.)

## How the loop advances
Each `/orchestrate` tick: `git pull main` → derive the merged-task set → if any PRs are still pending
review, report and wait for the next tick → when merges land, release the newly-unblocked wave. Human
merges between ticks are what move the build forward.

## Conflict recovery
If a PR conflicts with `main` after a sibling merges, the worker (or a fresh `/build-task <id>` run)
rebases the branch onto `main`, re-runs `make verify`, and force-updates the PR branch. Ownership
disjointness makes real content conflicts rare — most conflicts are only in generated/lock files,
which Wave 0 pins to minimize.
