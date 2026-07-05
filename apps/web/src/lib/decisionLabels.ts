import type { DecisionState, EscalationLevel } from "../types/contracts";

// A visual "tone" — always paired with an icon + text label in the UI, never color alone
// (docs/safety.md accessibility requirement: no status conveyed by color alone).
export type Tone = "danger" | "warning" | "info" | "neutral" | "success";

// `label` is the clinical short name; `description` is the plain-language line a non-biologist
// reads to understand what it actually means for the patient (used across the app).
export const decisionStateLabels: Record<
  DecisionState,
  { label: string; description: string; tone: Tone }
> = {
  ROUTINE_CONTINUE: {
    label: "On track",
    description: "On track. Continue as planned.",
    tone: "success",
  },
  OHSS_RISK_ESCALATE: {
    label: "Over-response risk",
    description:
      "The ovaries may be over-responding. This can become dangerous and needs a doctor now.",
    tone: "danger",
  },
  PREMATURE_LUTEINIZATION_FLAG: {
    label: "Cycle maturing too early",
    description: "Hormones are maturing the cycle too early.",
    tone: "warning",
  },
  POOR_RESPONSE_FLAG: {
    label: "Slow response",
    description: "The ovaries are responding slowly.",
    tone: "warning",
  },
  MISSING_TIMEPOINT: {
    label: "Missing check-up",
    description: "An expected check-up is missing.",
    tone: "info",
  },
  AMBIGUOUS_REQUIRES_REVIEW: {
    label: "Needs a human review",
    description: "The data is unclear. A human should review.",
    tone: "info",
  },
};

export const escalationLevelLabels: Record<EscalationLevel, { label: string; tone: Tone }> = {
  none: { label: "On track", tone: "success" },
  info: { label: "Watch", tone: "warning" },
  urgent: { label: "Needs attention now", tone: "danger" },
};
