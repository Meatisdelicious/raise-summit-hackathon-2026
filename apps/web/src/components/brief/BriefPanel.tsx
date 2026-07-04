import type { MonitoringBrief } from "../../types/contracts";
import { StateFlag } from "../shared/StateFlag";
import { CitationList } from "./CitationList";
import { ValidateBriefButton } from "./ValidateBriefButton";
import { decisionStateLabels } from "../../lib/decisionLabels";
import { escalationStatus } from "../../lib/glossary";
import { CheckIcon, InfoIcon, WarningIcon } from "../shared/icons";

function StatusIcon({ tone }: { tone: string }) {
  if (tone === "success") return <CheckIcon />;
  if (tone === "danger" || tone === "warning") return <WarningIcon />;
  return <InfoIcon />;
}

export function BriefPanel({
  brief,
  onValidated,
}: {
  brief: MonitoringBrief | null;
  onValidated: (brief: MonitoringBrief) => void;
}) {
  if (!brief) {
    return (
      <p className="brief-panel__empty">
        No read yet. Run the review and MILA's brief will appear here.
      </p>
    );
  }

  const status = escalationStatus[brief.escalation_level];

  return (
    <div className="brief-panel brief-reveal">
      <div className={`brief-status brief-status--${status.tone}`}>
        <span className="brief-status__icon" aria-hidden="true">
          <StatusIcon tone={status.tone} />
        </span>
        <div>
          <p className="brief-status__word">{status.word}</p>
          <p className="brief-status__hint">{status.hint}</p>
        </div>
      </div>

      {brief.states.length > 0 && (
        <div className="brief-panel__flags">
          {brief.states.map((state) => (
            <div key={state} className="brief-flag">
              <StateFlag state={state} />
              <p className="brief-flag__desc">{decisionStateLabels[state].description}</p>
            </div>
          ))}
        </div>
      )}

      <hr className="brief-panel__divider" />

      <div className="brief-panel__block">
        <p className="brief-panel__label">What MILA sees</p>
        <p>{brief.interpretation}</p>
      </div>

      <div className="brief-panel__block">
        <p className="brief-panel__label">Recommended action</p>
        <p>{brief.recommended_action}</p>
      </div>

      <div className="brief-panel__block">
        <p className="brief-panel__label">Grounded in protocol</p>
        <CitationList citations={brief.citations} />
      </div>

      <hr className="brief-panel__divider" />

      <div className="brief-panel__block">
        <p className="brief-panel__label">Human validation</p>
        <ValidateBriefButton brief={brief} onValidated={onValidated} />
      </div>
    </div>
  );
}
