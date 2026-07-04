# PRD — LoopCloser (condensed)

> This is the fast-grounding product brief. The **canonical** spec is [`docs/doc.md`](doc.md);
> when they disagree, `doc.md` wins.

## Problem
Clinician-authored follow-up instructions ("repeat this test within six months") get buried across
notes, orders, appointments, and reports. Proof of completion often lands later in a *different*
document, system, or naming convention — so no single record states whether the loop is truly closed.
This is a **document-grounded workflow problem**, not a medical-knowledge chatbot problem.

## Product
**LoopCloser** reads a longitudinal synthetic case, extracts the explicit instruction, **plans** where
proof should exist, **retrieves** evidence by class (orders, appointments, results, external results,
exceptions) more than once, **validates** candidates with deterministic tools, assigns one of six
constrained operational states, and **drafts the next staff action** — every conclusion carrying a
document/page citation, every external action gated on human approval.

It does **not** diagnose, interpret lab values, apply clinical guidelines, produce risk scores, or
prescribe. It answers: *"Is there sufficient documented evidence the requested follow-up was completed,
and if not, what task should staff review next?"*

## Users
Clinical-operations coordinators; quality & patient-safety teams; referral/diagnostic follow-up teams;
care coordinators; and the clinician who approves the final action.

## Core journey
1. Open a case from the **inbox** (workflow inbox, not a dashboard).
2. Click **Run follow-up review** → the agent shows its **plan** before acting.
3. Watch the **live trace**: multiple retrievals, a candidate **rejected** for a concrete reason
   (e.g. predates the instruction), a targeted re-search.
4. See the **constrained decision** with resolvable citations.
5. Review the **drafted task**, click **Approve** → persistent state changes + an audit event.

## Success metrics / release gates (spec §17.3)
- **False-closure = 0** on the demo corpus (the most important gate).
- Decision accuracy ≥ 90% across all synthetic recommendations.
- 100% of displayed citations resolve to the expected page.
- Primary + backup demo cases pass **5 consecutive** end-to-end runs.
- Task creation is idempotent (no duplicates on re-run).
- Privacy scan clean — no real identifier or original PDF anywhere.

## Judging (what to optimize)
Impact 25% · **Demo 50% (dominant)** · Creativity 15% · Pitch 10%. The signature moment — and the
creativity score — is the agent **refusing to close a loop** when a plausible document fails temporal
or semantic validation, then planning another search. Do not trade the demo path for extra features.

## Vultr fit (sponsor track)
Vultr Serverless Inference is on the **live critical path** (planning, extraction, query-gen, cited
explanation); Object Storage holds synthetic PDFs; Managed PostgreSQL holds cases/decisions/audit;
Compute hosts the FastAPI app + monitor. The trace must visibly show a live Vultr call.
