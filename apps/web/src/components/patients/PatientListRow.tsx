import { Link } from "react-router-dom";
import type { PatientWithBrief } from "../../hooks/usePatients";
import { EscalationBadge } from "../shared/EscalationBadge";
import { formatProtocol } from "../../lib/format";

export function PatientListRow({ patient, latestBrief }: PatientWithBrief) {
  return (
    <li className="patient-row">
      <Link to={`/patients/${patient.id}`} className="patient-row__link">
        <span className="patient-row__label">{patient.label}</span>
        <span className="patient-row__meta">
          {formatProtocol(patient.protocol)} · Day {patient.cycle_day}
          {patient.pcos_flag ? " · PCOS" : ""}
        </span>
        <span className="patient-row__status">
          {latestBrief ? (
            <EscalationBadge level={latestBrief.escalation_level} />
          ) : (
            <span className="badge badge--neutral">No run yet</span>
          )}
        </span>
      </Link>
    </li>
  );
}
