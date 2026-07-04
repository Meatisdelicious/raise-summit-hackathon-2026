import type { DecisionState, EscalationLevel } from "../types/contracts";

// A visual "tone" — always paired with an icon + text label in the UI, never color alone
// (docs/safety.md accessibility requirement: no status conveyed by color alone).
export type Tone = "danger" | "warning" | "info" | "neutral" | "success";

export const decisionStateLabels: Record<DecisionState, { label: string; tone: Tone }> = {
  ROUTINE_CONTINUE: { label: "Routine, continue", tone: "success" },
  OHSS_RISK_ESCALATE: { label: "OHSS risk", tone: "danger" },
  PREMATURE_LUTEINIZATION_FLAG: { label: "Premature luteinization", tone: "warning" },
  POOR_RESPONSE_FLAG: { label: "Poor response", tone: "warning" },
  MISSING_TIMEPOINT: { label: "Missing timepoint", tone: "info" },
  AMBIGUOUS_REQUIRES_REVIEW: { label: "Ambiguous, needs review", tone: "info" },
};

export const escalationLevelLabels: Record<EscalationLevel, { label: string; tone: Tone }> = {
  none: { label: "None", tone: "neutral" },
  info: { label: "Info", tone: "info" },
  urgent: { label: "Urgent", tone: "danger" },
};
