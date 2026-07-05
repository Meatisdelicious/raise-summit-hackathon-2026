# API contract — MILA

The seam between the FastAPI backend (`apps/api`, pkg `cyclesentinel`) and the React frontend
(`apps/web`, Raph). **Raph builds against this file** — it's the source of truth; he does not need the
backend running to start. All shapes are given as TypeScript so they can be copied into
`apps/web/src/types/`. The Python side mirrors them with identical field names (Pydantic).

Base URL: `/api`. All JSON. One SSE endpoint for the live agent trace.

---

## 1. Enums

```ts
export type Protocol = "antagonist" | "long_agonist" | "short_agonist" | "other";

export type DecisionState =
  | "ROUTINE_CONTINUE"
  | "OHSS_RISK_ESCALATE"
  | "PREMATURE_LUTEINIZATION_FLAG"
  | "POOR_RESPONSE_FLAG"
  | "MISSING_TIMEPOINT"
  | "AMBIGUOUS_REQUIRES_REVIEW";

export type EscalationLevel = "none" | "info" | "urgent";

export type RuleType = "ohss" | "luteinization" | "poor_responder" | "stimulation";
```

## 2. Core objects

```ts
export interface Patient {
  id: string;
  label: string;              // synthetic display label, e.g. "Patient K"
  protocol: Protocol;
  cycle_day: number;          // current day of stimulation
  amh: number;                // baseline anti-Müllerian hormone
  antral_follicle_count: number;
  pcos_flag: boolean;
}

export interface HormoneResult {
  id: string;
  patient_id: string;
  cycle_day: number;
  drawn_at: string;           // ISO datetime
  e2: number | null;          // estradiol
  lh: number | null;
  progesterone: number | null;
  fsh?: number | null;
  hcg?: number | null;
  mature_follicle_count?: number | null;  // from a monitoring scan, when available
}

export interface Citation {
  doc_id: string;             // e.g. "ohss_sop"
  rule_type: RuleType;
  page: number;               // the retrieved protocol/SOP page (visual doc retrieval)
  article: string;            // e.g. "§4.2" (read from the page's text layer)
  quote: string;              // the cited line(s)
  score?: number | null;      // retriever relevance score for that page
}

// A single hit returned by the visual retriever (Vultron Prime-8B) behind retrieve_protocol_rule.
export interface RetrievalHit {
  doc_id: string;
  rule_type: RuleType;
  page: number;
  score: number;              // Prime-8B relevance score
  text: string;               // the page's text layer (fed to the text-only LLM for grounding)
  article: string;
}

export interface ComputedSignal {
  name: string;               // "e2_rate" | "ohss_composite" | "progesterone_for_day" | ...
  value: number | string;
  detail: string;             // human-readable, e.g. "E2 +142%/day"
  tripped: boolean;           // did this signal cross its threshold?
}

export interface MonitoringBrief {
  id: string;
  patient_id: string;
  result_id: string;
  run_id: string;
  states: DecisionState[];         // may hold >1 flag (e.g. OHSS + luteinization)
  interpretation: string;          // trajectory-context interpretation
  recommended_action: string;
  citations: Citation[];           // every clause grounds to one of these
  escalation_level: EscalationLevel;
  validated_by: string | null;     // set once a human validates
  validated_at: string | null;
  created_at: string;
}
```

## 3. REST endpoints

```text
GET  /api/patients                         -> Patient[]
GET  /api/patients/{id}                     -> Patient
GET  /api/patients/{id}/results             -> HormoneResult[]        (the trajectory, ordered by cycle_day)
GET  /api/patients/{id}/latest-brief        -> MonitoringBrief | null

POST /api/patients/{id}/runs                 -> { run_id: string }    (start an agent run on the latest/new result)
     body: { result_id?: string }           (defaults to the newest result)
GET  /api/runs/{run_id}                       -> RunSummary
GET  /api/runs/{run_id}/events                -> text/event-stream    (SSE — see §4)

POST /api/briefs/{id}/validate                -> MonitoringBrief      (biologist approves; sets validated_by/at, may escalate)
     body: { validated_by: string, edits?: Partial<MonitoringBrief> }
POST /api/briefs/{id}/reject                  -> MonitoringBrief
     body: { validated_by: string, reason: string }

POST /api/demo/reset                          -> { ok: true }         (restore synthetic demo state)
GET  /api/health                              -> { status: "ok" }
GET  /api/ready                               -> { ready: boolean }
```

```ts
export interface RunSummary {
  run_id: string;
  patient_id: string;
  result_id: string;
  final_states: DecisionState[];
  brief_id: string | null;
  started_at: string;
  finished_at: string | null;
  step_count: number;
}
```

## 4. SSE agent trace — `GET /api/runs/{run_id}/events`

The live "money shot": the frontend renders these in order as the agent works. Each message is
`data: <json>\n\n`, discriminated by `type`. Frozen event union:

```ts
export type AgentEvent =
  | { type: "plan";               run_id: string; step: number; plan: string[] }
  | { type: "retrieve";           run_id: string; step: number; what: "patient_context" | "trajectory"; summary: string }
  | { type: "compute";            run_id: string; step: number; signal: ComputedSignal }
  | { type: "branch";             run_id: string; step: number; reason: string; rule_type: RuleType }   // why it's about to retrieve a rule
  | { type: "retrieve_rule";      run_id: string; step: number; rule_type: RuleType; hits: RetrievalHit[]; citation: Citation }  // visual doc retrieval (Prime-8B): pages + scores
  | { type: "action";             run_id: string; step: number; name: "dose_adjustment" | "next_draw_timing"; detail: string }
  | { type: "brief";              run_id: string; step: number; brief: MonitoringBrief }
  | { type: "escalate";           run_id: string; step: number; level: EscalationLevel; to: string }    // e.g. "biologist"
  | { type: "error";              run_id: string; message: string }
  | { type: "done";               run_id: string; final_states: DecisionState[] };
```

**Demo note for the UI:** highlight each `branch` → `retrieve_rule` pair — that is the visible proof the
agent went back for another document *because of what it just computed*. The **routine** patient produces
`compute` events but **no** `branch`/`retrieve_rule` — showing the retrievals are computation-driven.

## 5. Notes for Raph
- You can build the whole UI against a mock implementing §3/§4 (sample objects for Patient K + a routine
  patient) before the backend is live. Keep names identical to this file.
- Charts: `GET /patients/{id}/results` is the time series (x = `cycle_day`, series = e2 / lh / progesterone).
- The brief view: render `interpretation` + `recommended_action`, and make each `Citation` clickable to
  show `article` + `quote`. Show `states[]` as flags and `escalation_level` prominently.
- Validation: the biologist action calls `POST /briefs/{id}/validate`; reflect `validated_by/at`.
- Retrieval is **visual** (Vultron Prime-8B over protocol/SOP page images). For the trace, the
  `retrieve_rule` event carries `hits: RetrievalHit[]` (pages + scores) plus the chosen `citation` — you
  can show the retrieved **page** (and its score) as the visible proof the agent fetched a specific
  document. Citations are **page-based**: link each `Citation` to `doc_id` + `page` + `article` + `quote`.
