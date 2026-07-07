# MILA — PRD

**Track:** RAISE Summit Hackathon 2026 — Statement Two, Vultr enterprise agent
**Type:** Web-based, document-grounded clinical-operations agent (internal triage & escalation)
**Data policy:** Synthetic data only in the repo and the hosted demo

---

## One-sentence pitch
> MILA sits between the hormone assay and the clinician: for every new monitoring result in an
> IVF stimulation cycle, it rebuilds the patient's trajectory, computes the risk signals, pulls the
> exact protocol rule that the computation says applies, and hands the biologist a cited, ready-to-validate
> escalation brief — before a missed or mis-timed value wrecks the cycle.

## The problem
In assisted reproduction (PMA/IVF), women undergo **serial hormonal monitoring** (estradiol E2,
LH, progesterone, sometimes FSH/hCG) on tight timing. One mis-timed or missed value cascades:

- **OHSS** (ovarian hyperstimulation syndrome) — a real, sometimes life-threatening complication. Catching
  the *trajectory* early changes management (coasting, trigger modification, freeze-all, cancellation).
- **Premature luteinization / LH surge** — a progesterone rise at the wrong cycle day silently ruins the
  fresh-transfer odds; the decision it forces (freeze-all) is time-sensitive and easy to miss.
- **Poor response** — detected too late means a wasted, expensive cycle in a patient who may not get many
  attempts.

Today these get caught by a human scanning results, or not until the clinician's later review. The lab
delivers raw numbers, not intelligent escalation.

**Money & impact angle:** a cancelled or mismanaged cycle wastes **thousands of euros** and scarce clinic
capacity. For the lab, being the partner that delivers **intelligent critical-value escalation** (not raw
numbers) is a premium B2B differentiator with fertility centers.

## Who it's for (and who it is NOT for)
- **Enterprise user:** the **lab biologist** (e.g. Mlab) and the **prescribing PMA clinician**.
- **Never the patient.** MILA is professional clinical-decision-support / internal triage. It
  drafts an escalation; a human validates before anything reaches the clinic or patient. This keeps it off
  the "medical-advice bot" banned list; the reasoned brief + escalation (not a screen of charts) keeps it
  off the "dashboard" banned list.

## Core user journey
1. A new hormone result lands for a patient in stimulation.
2. MILA runs its agent loop and produces a **monitoring brief** with an escalation flag.
3. The **biologist validates** (or edits/rejects) the brief → an escalation call/alert goes to the clinician.
4. Every clause of the brief links to the **protocol/SOP article** it's grounded in.

## The agent loop (why it's an agent, not RAG)
1. **Plan** what's needed to interpret the new value.
2. **Retrieve patient state** — protocol type, cycle day, baseline (AMH, antral follicle count, PCOS).
3. **Retrieve the trajectory** — prior serial results (the stateful time series).
4. **Compute** (deterministic) — E2 rate-of-rise, E2-per-mature-follicle, OHSS composite, progesterone-vs-day.
5. **Branch → conditional retrieval** — *which* rule to pull is decided by what step 4 found: OHSS SOP,
   premature-luteinization rule (cycle-day-dependent), or poor-responder criteria.
6. **Compute the next action** — dose-adjustment range or next-draw timing.
7. **Decide & output** — a cited brief + escalation flag for human validation.

### The "not RAG" thesis (the pitch centerpiece)
> The conditional retrievals in step 5 **cannot** be issued up front, because *which* rule the agent needs
> is unknown until step 4's computation reveals the concern — and that computation is impossible until
> steps 2–3 rebuild the trajectory. The information-dependency graph **forbids** a retrieve-then-answer
> architecture. A judge who can't collapse the workflow into one retrieval has conceded the point.

**The trap:** if built as "today's value → threshold table → normal/abnormal," it degrades to a rules
engine + DB. The agentic-ness lives in (a) trajectory reasoning, (b) computation-driven conditional
retrieval, (c) the branching escalation tree. The demo **must visibly show the agent going back for a 2nd
and 3rd document because of what it just computed.**

## Success metrics (release-gate intent)
- The killer demo case reliably shows **≥2 computation-triggered conditional retrievals**, **≥2 tool calls**,
  **a branch**, and **a cited escalation** — live.
- **Every brief clause resolves** to a real protocol/SOP article (citation validity 100%).
- **No false reassurance:** a case that should escalate never returns `ROUTINE_CONTINUE`. When data is
  missing/ambiguous → `MISSING_TIMEPOINT` / `AMBIGUOUS_REQUIRES_REVIEW`, never a silent "normal."
- **Privacy scan clean** — zero real hormone data / identifiers in the repo or demo.
- Primary + backup demo cases pass repeated runs.

## Judging fit
Impact 25% · **Demo 50% (dominant)** · Creativity 15% · Pitch 10%.
- **Impact:** life-threatening OHSS + cycle-loss stakes; clear B2B lab buyer; auditable escalation, not advice.
- **Demo:** the computation-driven conditional retrieval is the money shot.
- **Creativity:** the dependency-graph-forbids-RAG argument.
- **Pitch + Vultr:** an all-on-Vultr, Qwen3.5-lineage stack — **Kimi K2 Instruct** (reasoning/tool LLM)
  + **Vultron Prime-8B visual document retrieval** over the protocol/SOP pages — hosted with the vector
  store in an **EU region, HDS-aligned**. The sovereign alternative to hormone data leaking abroad; a
  clean "future of work in healthcare" story. The visual VDR reinforces the "not RAG" thesis: the agent
  fetches a *specific protocol page* only once a computation says which rule applies.
