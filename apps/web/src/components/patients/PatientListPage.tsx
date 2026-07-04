import { usePatients } from "../../hooks/usePatients";
import { PatientListRow } from "./PatientListRow";

export function PatientListPage() {
  const { patients, loading, error } = usePatients();

  if (loading) return <p className="loading-state">Loading patients…</p>;
  if (error) return <p role="alert" className="alert">{error}</p>;

  return (
    <section aria-labelledby="patient-list-heading">
      <div className="page-head">
        <p className="eyebrow">Patients in stimulation</p>
        <h1 id="patient-list-heading" className="page-head__title">
          Who needs a doctor's attention?
        </h1>
        <p className="page-head__lede">
          MILA reviews each patient's hormone response and flags the ones that need a closer look —
          so the team can focus on what matters. Open a patient to see how it reached its read.
        </p>
      </div>
      <ul className="patient-list">
        {patients.map(({ patient, latestBrief }) => (
          <PatientListRow key={patient.id} patient={patient} latestBrief={latestBrief} />
        ))}
      </ul>
    </section>
  );
}
