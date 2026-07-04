<!-- Title: T<id>: <summary> · Labels: wave:<n>, task:T<id> · Base: main -->

## Task
Closes task: **T<id>** — <one-line summary>

## Definition of Done (AGENTS.md §11)
- [ ] Behavior matches the task `exit_condition` and `docs/doc.md`
- [ ] Module unit/integration tests written and green
- [ ] `make verify` green in **replay** mode (paste summary below)
- [ ] Diff touches **only** this task's `owned_paths` (`make ownership TASK=T<id>` passes)
- [ ] `make privacy` clean; no secrets; `data/private/` untouched
- [ ] Any citations produced resolve to the expected page
- [ ] Non-negotiables respected (synthetic-only · Vultr live path · false-closure=0 · no medical advice · 6 states / 8 tools)

## Owned-paths attestation
I edited only paths declared in `tasks/T<id>.md`. ✅

## `make verify` summary
```
<paste the tail of `make verify` here>
```

## Cassettes updated? (Y/N)
<N unless this task re-recorded from live Vultr>

## Evidence (agent/UI tasks)
<screenshot / trace / short recording of the demo-path beat this task affects>

---
> Humans merge; agents never merge. Do not merge your own PR.
