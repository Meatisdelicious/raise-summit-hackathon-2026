import type { DecisionState } from "../../types/contracts";
import { decisionStateLabels, type Tone } from "../../lib/decisionLabels";
import { CheckIcon, InfoIcon, WarningIcon } from "./icons";

function toneIcon(tone: Tone) {
  switch (tone) {
    case "success":
      return CheckIcon;
    case "danger":
    case "warning":
      return WarningIcon;
    default:
      return InfoIcon;
  }
}

export function StateFlag({ state }: { state: DecisionState }) {
  const { label, tone } = decisionStateLabels[state];
  const Icon = toneIcon(tone);
  return (
    <span className={`badge badge--${tone}`}>
      <Icon />
      {label}
    </span>
  );
}
