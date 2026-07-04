import type { MonitoringBrief } from "../../types/contracts";
import { StateFlag } from "../shared/StateFlag";
import { EscalationBadge } from "../shared/EscalationBadge";
import { CitationList } from "./CitationList";
import { ValidateBriefButton } from "./ValidateBriefButton";

export function BriefPanel({
  brief,
  onValidated,
}: {
  brief: MonitoringBrief | null;
  onValidated: (brief: MonitoringBrief) => void;
}) {
  if (!brief) {
    return <p className="brief-panel__empty">No brief yet — run the monitoring review first.</p>;
  }

  return (
    <div className="brief-panel">
      <div className="brief-panel__flags">
        {brief.states.map((state) => (
          <StateFlag key={state} state={state} />
        ))}
        <EscalationBadge level={brief.escalation_level} />
      </div>

      <h3>Interpretation</h3>
      <p>{brief.interpretation}</p>

      <h3>Recommended action</h3>
      <p>{brief.recommended_action}</p>

      <h3>Citations</h3>
      <CitationList citations={brief.citations} />

      <h3>Validation</h3>
      <ValidateBriefButton brief={brief} onValidated={onValidated} />
    </div>
  );
}
