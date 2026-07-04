import { Link } from "react-router-dom";
import type { PatientWithBrief } from "../../hooks/usePatients";
import { EscalationBadge } from "../shared/EscalationBadge";
import { friendlyProtocol, escalationStatus } from "../../lib/glossary";

export function PatientListRow({ patient, latestBrief }: PatientWithBrief) {
  const status = latestBrief ? escalationStatus[latestBrief.escalation_level] : null;

  return (
    <li className="patient-row">
      <Link to={`/app/patients/${patient.id}`} className="patient-row__link">
        <span className="patient-row__id">
          <span className="patient-row__label">{patient.label}</span>
          <span className="patient-row__read">
            Day {patient.cycle_day} of stimulation
            {patient.pcos_flag ? " · higher over-response risk (PCOS)" : ""}
          </span>
          <span className="patient-row__meta">{friendlyProtocol(patient.protocol)}</span>
        </span>
        <span className="patient-row__status">
          {latestBrief ? (
            <>
              <EscalationBadge level={latestBrief.escalation_level} />
              {status && <span className="patient-row__hint">{status.hint}</span>}
            </>
          ) : (
            <span className="badge badge--neutral">Not reviewed yet</span>
          )}
        </span>
      </Link>
    </li>
  );
}
