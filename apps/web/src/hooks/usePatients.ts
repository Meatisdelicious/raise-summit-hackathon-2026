import { useEffect, useState } from "react";
import { api } from "../api";
import type { MonitoringBrief, Patient } from "../types/contracts";

export interface PatientWithBrief {
  patient: Patient;
  latestBrief: MonitoringBrief | null;
}

export function usePatients(): {
  patients: PatientWithBrief[];
  loading: boolean;
  error: string | null;
} {
  const [patients, setPatients] = useState<PatientWithBrief[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const list = await api.listPatients();
        const withBriefs = await Promise.all(
          list.map(async (patient) => ({
            patient,
            latestBrief: await api.getLatestBrief(patient.id),
          })),
        );
        if (!cancelled) setPatients(withBriefs);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load patients.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { patients, loading, error };
}
