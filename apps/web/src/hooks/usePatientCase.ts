import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { HormoneResult, MonitoringBrief, Patient } from "../types/contracts";

export function usePatientCase(patientId: string): {
  patient: Patient | null;
  results: HormoneResult[];
  latestBrief: MonitoringBrief | null;
  loading: boolean;
  error: string | null;
  refetchBrief: () => Promise<void>;
} {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [results, setResults] = useState<HormoneResult[]>([]);
  const [latestBrief, setLatestBrief] = useState<MonitoringBrief | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [patientData, resultsData, briefData] = await Promise.all([
          api.getPatient(patientId),
          api.getPatientResults(patientId),
          api.getLatestBrief(patientId),
        ]);
        if (!cancelled) {
          setPatient(patientData);
          setResults(resultsData);
          setLatestBrief(briefData);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load the case.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  const refetchBrief = useCallback(async () => {
    const briefData = await api.getLatestBrief(patientId);
    setLatestBrief(briefData);
  }, [patientId]);

  return { patient, results, latestBrief, loading, error, refetchBrief };
}
