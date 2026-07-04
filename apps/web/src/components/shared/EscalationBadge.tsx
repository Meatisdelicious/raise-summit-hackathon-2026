import type { EscalationLevel } from "../../types/contracts";
import { escalationLevelLabels, type Tone } from "../../lib/decisionLabels";
import { CheckIcon, InfoIcon, WarningIcon } from "./icons";

function toneIcon(tone: Tone) {
  switch (tone) {
    case "danger":
    case "warning":
      return WarningIcon;
    case "success":
    case "neutral":
      return CheckIcon;
    default:
      return InfoIcon;
  }
}

export function EscalationBadge({ level }: { level: EscalationLevel }) {
  const { label, tone } = escalationLevelLabels[level];
  const Icon = toneIcon(tone);
  return (
    <span className={`badge badge--${tone}`} aria-label={`Escalation level: ${label}`}>
      <Icon />
      {label}
    </span>
  );
}
