import type { EscalationLevel } from "../types/contracts";
import type { Tone } from "./decisionLabels";

// Plain-language layer for non-biologists (hackathon judges, investors).
// The whole point of the demo is to make a highly technical, medical product feel clear and calm.
// These map raw clinical identifiers -> the words a person actually recognises.

export interface Friendly {
  friendly: string; // the headline a non-expert reads
  tooltip?: string; // one short clarifying sentence
}

// --- Computed signals (ComputedSignal.name) ------------------------------------------------
// The friendly name is shown as the headline; the raw `detail` stays as secondary evidence.
export const signalLabels: Record<string, Friendly> = {
  e2_rate: {
    friendly: "How fast estrogen is rising",
    tooltip: "A fast climb can mean the ovaries are over-responding.",
  },
  e2_per_follicle: {
    friendly: "Estrogen per follicle",
    tooltip: "Estrogen shared across the growing follicles — a balance check.",
  },
  ohss_composite: {
    friendly: "Over-response risk score",
    tooltip: "A combined score for how strongly the ovaries are reacting.",
  },
  progesterone_for_day: {
    friendly: "Progesterone vs. today's safe level",
    tooltip: "If progesterone rises too early, egg timing suffers.",
  },
  response_curve: {
    friendly: "On track vs. expected",
    tooltip: "Is the hormone response following the expected curve?",
  },
  monitoring_gap: {
    friendly: "Monitoring on schedule?",
    tooltip: "Checks that no expected blood draw or scan was missed.",
  },
};

export function signalLabel(name: string): Friendly {
  return (
    signalLabels[name] ?? {
      friendly: name
        .split("_")
        .map((word) => word[0]?.toUpperCase() + word.slice(1))
        .join(" "),
    }
  );
}

// --- Clinical terms (tooltips via <Term>) --------------------------------------------------
export const terms: Record<string, string> = {
  E2: "Estrogen (estradiol) — the main hormone that rises as follicles grow.",
  OHSS: "Ovarian over-response — when the ovaries react too strongly; can become serious.",
  PCOS: "A hormonal condition that raises the over-response risk.",
  progesterone: "Rises too early → egg timing suffers.",
  "cycle day": "Day of the stimulation cycle.",
  AMH: "A marker of ovarian reserve (how many eggs are available).",
  AFC: "Antral follicle count — a marker of ovarian reserve, seen on ultrasound.",
  LH: "Luteinizing hormone — the surge that matures and releases the egg.",
};

// --- Escalation -> calm plain status -------------------------------------------------------
// Never show the raw enum ("urgent") to a judge; show what it means for the patient.
export interface PlainStatus {
  word: string;
  tone: Tone;
  hint: string;
}

export const escalationStatus: Record<EscalationLevel, PlainStatus> = {
  none: { word: "On track", tone: "success", hint: "Responding as expected — continue as planned." },
  info: { word: "Watch", tone: "warning", hint: "Something to keep an eye on — flagged for review." },
  urgent: {
    word: "Needs attention now",
    tone: "danger",
    hint: "A doctor should look at this without delay.",
  },
};

// Humanise a protocol name into something a non-expert reads without a glossary.
export function friendlyProtocol(protocol: string): string {
  switch (protocol) {
    case "antagonist":
      return "Antagonist protocol";
    case "long_agonist":
      return "Long agonist protocol";
    case "short_agonist":
      return "Short agonist protocol";
    default:
      return "Stimulation protocol";
  }
}

// A one-line read of ovarian reserve from AMH, in words rather than numbers.
export function reserveHint(amh: number): string {
  if (amh >= 4.5) return "High ovarian reserve";
  if (amh >= 1.5) return "Typical ovarian reserve";
  return "Low ovarian reserve";
}
