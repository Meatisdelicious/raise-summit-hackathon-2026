---
description: Lead build orchestrator — compute the next unblocked wave and spawn parallel worktree workers that each open a PR.
---

You are the **lead orchestrator** for the LoopCloser build. Run under `/loop /orchestrate` (self-paced).
Each invocation performs **exactly one tick** and then stops so the human can merge PRs.

## Read first (every tick)
- `AGENTS.md`, `docs/TASKS.md`, and all `tasks/*.md` frontmatter.
- Never merge PRs yourself. Never build product code yourself — you only dispatch workers.

## Tick procedure

1. **Sync state.**
   - `git checkout main && git pull --ff-only`.
   - Merged-task set: `gh pr list --state merged --json number,labels,title` → read `task:<id>` labels.
     A task is **done** iff its PR is merged to `main`. Cross-check `git log` for the task IDs.
   - Open-PR set: `gh pr list --state open --json number,labels,title` → tasks currently `in-review`.

2. **Enforce the Phase-0 privacy gate (hard block).**
   - If **T00, T01, T02 are not all merged**, the ONLY assignable work is Wave 0. Do not dispatch any
     Wave ≥1 task.
   - Before dispatching anything, confirm the privacy gate passes: run `make privacy` (or `/privacy-gate`).
     If it fails, **STOP the entire loop**, report the hits, and dispatch nothing.

3. **Compute the next unblocked wave.**
   - A task is **ready** iff: not done, not already open as a PR, and every `depends_on` task is done.
   - Select ready tasks from the **lowest incomplete wave** (don't skip waves). Cap concurrent workers
     at **4** (configurable). Assignments are held in-memory this tick — tasks are disjoint by
     construction, so there is no shared claim state to write.

4. **Dispatch workers (in parallel, one message, multiple Agent calls).**
   For each selected task `<id>` with owner subagent `<sub>` from its frontmatter, spawn:
   `Agent(subagent_type: <sub>, isolation: "worktree", run_in_background: true)` with a prompt that says:
   > Run the `/build-task <id>` workflow. Read `tasks/<id>.md` and `AGENTS.md`. You are in an isolated
   > worktree on branch `task/w<wave>-<id>-<slug>`. Implement ONLY within `owned_paths`, consume the
   > frozen `docs/CONTRACTS.md` seams, run `make verify` until green, then open a PR with the template
   > and the `wave:<n>`/`task:<id>` labels. If blocked or needing a seam/dep change, STOP and report.
   (If the `EnterWorktree` tool is available, workers use it; otherwise `git worktree add`.)

5. **Report & stop.**
   - Wait for the dispatched workers to finish opening their PRs, then summarize: which PRs opened
     (with URLs), their CI status (`gh pr checks`), and which tasks remain blocked and why.
   - Tell the human exactly which PRs are ready to review/merge.
   - **Do not merge.** End the tick.

## Self-pacing (between ticks)
- If PRs from the last wave are still open/pending review → there is nothing new to dispatch; report
  "waiting on human merge of PRs #… " and end. The next tick re-checks.
- If merges have landed since last tick → advance to the next unblocked wave.
- If **all tasks (through T51) are merged** → run the final gates:
  `make eval` (release gates) and the 5-consecutive-run demo check (`make e2e` ×5 on primary+backup).
  If green → announce the build is complete and **stop the loop**. If any gate fails → create a fix
  task spec under `tasks/` (e.g. `tasks/Tfix-<n>.md`, owner = the relevant subagent, `owned_paths`
  scoped to the failing module) and dispatch it next tick.

## Notes
- T14/T30/T32 touch the inference seam; if cassettes need refreshing, flag the human to run
  `/record-cassettes` (needs Vultr creds) — do not attempt live Vultr calls without credentials.
- Keep the tick idempotent: re-running after a crash must not double-dispatch a task that already has
  an open PR.
