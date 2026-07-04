import { usePatients } from "../../hooks/usePatients";
import { PatientListRow } from "./PatientListRow";

export function PatientListPage() {
  const { patients, loading, error } = usePatients();

  if (loading) return <p>Loading patients…</p>;
  if (error) return <p role="alert">{error}</p>;

  return (
    <section aria-labelledby="patient-list-heading">
      <h1 id="patient-list-heading">Patients in stimulation</h1>
      <ul className="patient-list">
        {patients.map(({ patient, latestBrief }) => (
          <PatientListRow key={patient.id} patient={patient} latestBrief={latestBrief} />
        ))}
      </ul>
    </section>
  );
}
