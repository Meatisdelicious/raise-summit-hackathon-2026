# Cycle Sentinel — technical spec

Lean build spec for the ovarian-stimulation monitoring & escalation agent. Product framing is in
[`PRD.md`](PRD.md); the API/TS contract is in [`CONTRACTS.md`](CONTRACTS.md); safety in [`safety.md`](safety.md).

---

## 1. Scope

**In scope:** ingest a new serial hormone result for a patient in IVF stimulation; rebuild her trajectory;
run deterministic calculators; conditionally retrieve the governing protocol/SOP rule; emit a cited
monitoring brief with an escalation flag for human validation; detect a missing/mis-timed monitoring point.

**Out of scope (hard boundary):** advising the patient; autonomous diagnosis, treatment, dosing decisions,
or prescription; acting without human validation; interpreting anything not grounded in a cited protocol/SOP
article. See [`safety.md`](safety.md).

## 2. The agent loop

```text
NEW_RESULT
  │
  ▼
PLAN ─────────────► what's needed to interpret this value?
  │
  ▼
RETRIEVE patient_context   (protocol, cycle day, AMH, AFC, PCOS)      ── tool: get_patient_context
  │
  ▼
RETRIEVE trajectory        (prior serial results = time series)       ── tool: get_trajectory
  │
  ▼
COMPUTE signals            (deterministic calculators)                ── tools: compute_*
  │
  ├─ OHSS composite trips ─────────► RETRIEVE ohss_sop        (cite) ─┐
  ├─ P4 high for cycle day ───────► RETRIEVE luteinization_rule(cite)─┤  ← conditional, chosen BY the
  ├─ response flat vs curve ──────► RETRIEVE poor_responder   (cite) ─┤    computation (the "not RAG" core)
  └─ nothing trips ───────────────► routine branch (minimal output) ──┘
  │
  ▼
COMPUTE action             (dose-adjust range OR next-draw timing)    ── tools: lookup_dose_adjustment /
  │                                                                      compute_next_draw_timing
  ▼
DECIDE state + DRAFT brief (cited) ──► ESCALATE flag ──► HUMAN VALIDATION ──► clinician alert
```

Constraints: ≤ 10 steps per run; each conditional rule retrieved at most once; invalid model output
retried once against the schema, then `AMBIGUOUS_REQUIRES_REVIEW`. The LLM plans/interprets/writes prose;
**deterministic calculators + rules decide the escalation flag** — never an autonomous clinical verdict.

## 3. Tool registry (deterministic)

| Tool | Purpose |
|---|---|
| `get_patient_context` | protocol type, current cycle day, baseline markers (AMH, AFC, PCOS flag) |
| `get_trajectory` | the patient's prior serial results (time series) up to now |
| `compute_e2_rate` | E2 rate-of-rise between the last draws (absolute + %/day) |
| `compute_e2_per_follicle` | estradiol per mature follicle (needs follicle count from context/scan) |
| `compute_ohss_composite` | OHSS-risk composite from E2 level, rate, follicle count, PCOS flag |
| `check_progesterone_for_day` | progesterone vs the cycle-day-dependent threshold |
| `retrieve_protocol_rule` | **conditional** vector retrieval of a rule, filtered by `rule_type` (ohss / luteinization / poor_responder / stimulation), returns text + article citation |
| `lookup_dose_adjustment` | gonadotropin dose-adjustment range for the situation (from protocol table) |
| `compute_next_draw_timing` | next monitoring interval given the trajectory (e.g. 24h vs 48h) |
| `create_monitoring_brief` | assemble the cited brief object |
| `escalate_to_biologist` | attach an escalation flag/level; records that human validation is required |

Tool args/results are Pydantic-validated (schemas in [`CONTRACTS.md`](CONTRACTS.md)). The model may not
call an unregistered tool.

## 4. Escalation / decision states (constrained set)

| State | Meaning | Typical action |
|---|---|---|
| `ROUTINE_CONTINUE` | trajectory within expected bounds | continue protocol; standard next draw |
| `OHSS_RISK_ESCALATE` | OHSS composite trips | cite OHSS SOP → coasting / trigger-swap / freeze-all / cancel; escalate |
| `PREMATURE_LUTEINIZATION_FLAG` | P4 elevated for this cycle day | cite luteinization rule → consider freeze-all; escalate |
| `POOR_RESPONSE_FLAG` | response flat vs expected curve | cite poor-responder criteria → dose/plan review; escalate |
| `MISSING_TIMEPOINT` | a needed monitoring draw didn't happen | flag the gap; request the missing draw |
| `AMBIGUOUS_REQUIRES_REVIEW` | conflicting/insufficient data or step/limit exceeded | route to biologist; never a silent "normal" |

A run may raise more than one flag (e.g. the killer case = OHSS + luteinization). **Fail safe:** anything
that should escalate must never resolve to `ROUTINE_CONTINUE`.

## 5. Deterministic calculators (the computed signals)

Implemented as pure functions with unit tests; **no LLM**. Thresholds live in the synthetic protocol so
they're cited, not hardcoded magic numbers:
- **E2 rate-of-rise** between consecutive draws (Δ and %/day) — steep rise is an OHSS precursor.
- **E2 per mature follicle** — distinguishes "high E2 from many follicles" vs an outlier.
- **OHSS composite** — combine E2 level, rate, follicle count, PCOS flag into a risk tier.
- **Progesterone-vs-cycle-day** — the threshold is day-dependent (needs the cycle day from step 2).
- **Response-curve check** — compare the trajectory to the protocol's expected stimulation curve.
- **Next-draw timing** — interval from trajectory volatility (accelerating → shorter interval).

## 6. Synthetic data model

- **`patients`** — id, protocol type (`antagonist` / `long_agonist` / …), baseline `amh`, `antral_follicle_count`,
  `pcos_flag`, cycle start date.
- **`results`** — id, patient_id, `cycle_day`, `drawn_at`, and analytes: `e2`, `lh`, `progesterone`,
  optional `fsh`, `hcg`, plus optional `mature_follicle_count` (from a monitoring scan).
- **`briefs`** — id, patient_id, result_id, `state[]`, `interpretation`, `recommended_action`,
  `citations[]`, `escalation_level`, `validated_by`, `validated_at`, `run_id`.
- **`agent_runs` / `steps`** — run id, ordered steps (tool name, args summary, result summary, latency),
  final state, correlation id — powers the live trace + audit.
- **Protocol/SOP corpus** (vector store) — a synthetic **stimulation protocol**, **OHSS-prevention SOP**,
  **premature-luteinization rule**, **poor-responder management**, each split into numbered
  **articles/sections** for per-line citation.

## 7. Synthetic demo cases (ground truth)

| Case | Setup | Expected behavior |
|---|---|---|
| **K — killer** | Day 8, antagonist, PCOS, steep E2 rise, P4 borderline for day 8 | rebuild curve → OHSS composite trips → retrieve OHSS SOP §x → **also** P4-for-day trips → retrieve luteinization rule §y → next-draw 24h → brief with **both** flags, cited, escalated |
| **R — routine (backup)** | normal E2 curve, P4 normal for day | `ROUTINE_CONTINUE`, minimal output, no conditional retrieval |
| **P — poor responder** | flat E2 vs expected curve | `POOR_RESPONSE_FLAG`, retrieve poor-responder criteria, escalate |
| **M — missing timepoint** | expected day-N draw absent | `MISSING_TIMEPOINT`, request the missing draw |

The **routine** case is the control that proves the agent doesn't retrieve the OHSS/luteinization docs
when the computation doesn't call for them — which is what makes the killer case's extra retrievals mean
something.

## 8. Vultr architecture (on the critical path)

- **Vultr Serverless Inference** — planning, interpretation-in-trajectory-context, brief prose generation,
  tool-selection. Temperature 0. On the live path (must be visible in the demo trace).
- **Vultr vector store (EU region)** — the protocol/SOP corpus; queried by `retrieve_protocol_rule`.
  pgvector on Vultr Managed PostgreSQL (EU) is the default; keep it swappable.
- **Vultr Object Storage** — synthetic protocol/SOP source docs (private bucket).
- **Vultr Compute** — hosts the FastAPI app.
- **Sovereignty story:** hormone data + protocol corpus stay in an EU region, **HDS-aligned** — the
  sovereign alternative to sensitive fertility data leaving the EU.

## 9. Stack & inference modes

- **Backend:** Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy + pgvector · pytest. Package `cyclesentinel`
  under `apps/api/`.
- **Frontend:** React + TypeScript (Raph), builds against [`CONTRACTS.md`](CONTRACTS.md).
- **Inference modes** (env `CS_INFERENCE_MODE`): `live` (Vultr — the demo), `replay` (recorded
  cassettes — CI/tests, deterministic), `stub` (canned outputs — unit tests). CI never calls Vultr.

## 10. Demo & safety

The 2-minute demo is in [`demo-script.md`](demo-script.md); the safety/privacy boundary in
[`safety.md`](safety.md). Both are binding.
