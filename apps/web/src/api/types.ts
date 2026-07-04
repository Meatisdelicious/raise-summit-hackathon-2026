import type { HormoneResult, MonitoringBrief, Patient, RunSummary } from "../types/contracts";
import type { RunEventCallbacks } from "../mocks/server/eventStream";

// The seam every screen depends on. mockClient.ts and client.ts both implement this so components
// never know (or care) which one is active.
export interface Api {
  listPatients(): Promise<Patient[]>;
  getPatient(id: string): Promise<Patient>;
  getPatientResults(id: string): Promise<HormoneResult[]>;
  getLatestBrief(id: string): Promise<MonitoringBrief | null>;
  startRun(patientId: string, resultId?: string): Promise<{ run_id: string }>;
  getRun(runId: string): Promise<RunSummary>;
  subscribeToRunEvents(runId: string, callbacks: RunEventCallbacks): () => void;
  validateBrief(
    briefId: string,
    validatedBy: string,
    edits?: Partial<MonitoringBrief>,
  ): Promise<MonitoringBrief>;
  rejectBrief(briefId: string, validatedBy: string, reason: string): Promise<MonitoringBrief>;
  resetDemo(): Promise<{ ok: true }>;
}
