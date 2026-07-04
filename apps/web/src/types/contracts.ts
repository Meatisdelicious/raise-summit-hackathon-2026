// Verbatim mirror of docs/CONTRACTS.md. This is the frozen seam between the FastAPI backend
// (apps/api, pkg cyclesentinel) and this frontend. Never rename a field here without updating
// docs/CONTRACTS.md first — the Python side must keep identical field names.

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

export interface Patient {
  id: string;
  label: string; // synthetic display label, e.g. "Patient K"
  protocol: Protocol;
  cycle_day: number; // current day of stimulation
  amh: number; // baseline anti-Müllerian hormone
  antral_follicle_count: number;
  pcos_flag: boolean;
}

export interface HormoneResult {
  id: string;
  patient_id: string;
  cycle_day: number;
  drawn_at: string; // ISO datetime
  e2: number | null; // estradiol
  lh: number | null;
  progesterone: number | null;
  fsh?: number | null;
  hcg?: number | null;
  mature_follicle_count?: number | null; // from a monitoring scan, when available
}

export interface Citation {
  doc_id: string; // e.g. "ohss_sop"
  rule_type: RuleType;
  page: number; // the retrieved protocol/SOP page (visual doc retrieval)
  article: string; // e.g. "§4.2" (read from the page's text layer)
  quote: string; // the cited line(s)
  score?: number | null; // retriever relevance score for that page
}

// A single hit returned by the visual retriever (Vultron Prime-8B) behind retrieve_protocol_rule.
export interface RetrievalHit {
  doc_id: string;
  rule_type: RuleType;
  page: number;
  score: number; // Prime-8B relevance score
  text: string; // the page's text layer (fed to the text-only LLM for grounding)
  article: string;
}

export interface ComputedSignal {
  name: string; // "e2_rate" | "ohss_composite" | "progesterone_for_day" | ...
  value: number | string;
  detail: string; // human-readable, e.g. "E2 +142%/day"
  tripped: boolean; // did this signal cross its threshold?
}

export interface MonitoringBrief {
  id: string;
  patient_id: string;
  result_id: string;
  run_id: string;
  states: DecisionState[]; // may hold >1 flag (e.g. OHSS + luteinization)
  interpretation: string; // trajectory-context interpretation
  recommended_action: string;
  citations: Citation[]; // every clause grounds to one of these
  escalation_level: EscalationLevel;
  validated_by: string | null; // set once a human validates
  validated_at: string | null;
  created_at: string;
}

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

// SSE agent trace — GET /api/runs/{run_id}/events
// The live "money shot": the frontend renders these in order as the agent works.
// Highlight each `branch` -> `retrieve_rule` pair: that is the visible proof the agent went back
// for another document *because of what it just computed*. The routine patient produces `compute`
// events but no `branch`/`retrieve_rule` events - showing the retrievals are computation-driven.
export type AgentEvent =
  | { type: "plan"; run_id: string; step: number; plan: string[] }
  | {
      type: "retrieve";
      run_id: string;
      step: number;
      what: "patient_context" | "trajectory";
      summary: string;
    }
  | { type: "compute"; run_id: string; step: number; signal: ComputedSignal }
  | { type: "branch"; run_id: string; step: number; reason: string; rule_type: RuleType }
  | {
      type: "retrieve_rule";
      run_id: string;
      step: number;
      rule_type: RuleType;
      hits: RetrievalHit[];
      citation: Citation;
    }
  | {
      type: "action";
      run_id: string;
      step: number;
      name: "dose_adjustment" | "next_draw_timing";
      detail: string;
    }
  | { type: "brief"; run_id: string; step: number; brief: MonitoringBrief }
  | { type: "escalate"; run_id: string; step: number; level: EscalationLevel; to: string }
  | { type: "error"; run_id: string; message: string }
  | { type: "done"; run_id: string; final_states: DecisionState[] };
