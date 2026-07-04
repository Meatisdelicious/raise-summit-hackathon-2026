# Two-minute demo script

Source of truth: [`docs/doc.md`](doc.md) §15. This is the path the whole build protects — do not
trade it for extra features (Demo = 50% of judging).

| Time | Beat | On screen |
|---|---|---|
| 0:00–0:15 | **Problem** | A synthetic clinician note, one sentence highlighted: "repeat this test within six months." |
| 0:15–0:30 | **Start** | Open the case → **Run follow-up review**. The agent shows its **plan** before calling any tool. |
| 0:30–0:55 | **Multiple retrievals** | Separate retrievals stream via SSE: source instruction → later internal results → external results / appointments. |
| 0:55–1:20 | **Signature moment** | The agent finds a result that *looks* like a match, then **rejects it because it predates the instruction**, and runs another targeted retrieval. Proves it isn't keyword matching. |
| 1:20–1:40 | **Decision** | `OPEN_OVERDUE` with reason + rejected-evidence reason. Open the **citations** to prove grounding. |
| 1:40–1:55 | **Enterprise action** | Agent drafts a coordinator task → clinician clicks **Approve** → DB state → `ACTION_PENDING`, audit event appears. |
| 1:55–2:00 | **Close** | "LoopCloser does not decide medicine. It makes sure an explicit clinical decision doesn't disappear between documents." |

## Backup case
A second preloaded case where a **valid external report closes the loop** (`COMPLETED`). If live
inference fails, the app preserves the **last successful run** and labels it clearly as a *recorded
run* — never pretending it is live.

## Checklist the demo must visibly show (spec §16.2)
Live Vultr call · explicit plan · ≥2 retrievals · a deterministic validation · a branch caused by
insufficient evidence · a cited decision · a real task-state mutation · human approval · an audit event.
