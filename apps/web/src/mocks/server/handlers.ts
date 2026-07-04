import type { HormoneResult, MonitoringBrief, Patient, RunSummary } from "../../types/contracts";
import { getStore, resetStore } from "./db";

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomDelay(minMs = 150, maxMs = 400): Promise<void> {
  return delay(minMs + Math.random() * (maxMs - minMs));
}

export async function listPatients(): Promise<Patient[]> {
  await randomDelay();
  return [...getStore().patients];
}

export async function getPatient(id: string): Promise<Patient> {
  await randomDelay();
  const patient = getStore().patients.find((p) => p.id === id);
  if (!patient) throw new Error(`Unknown patient: ${id}`);
  return patient;
}

export async function getPatientResults(id: string): Promise<HormoneResult[]> {
  await randomDelay();
  return [...(getStore().resultsByPatient.get(id) ?? [])];
}

export async function getLatestBrief(id: string): Promise<MonitoringBrief | null> {
  await randomDelay();
  return getStore().latestBriefByPatient.get(id) ?? null;
}

export async function startRun(
  patientId: string,
  _resultId?: string,
): Promise<{ run_id: string }> {
  await randomDelay();
  const store = getStore();
  const runId = [...store.runToPatient.entries()].find(([, pid]) => pid === patientId)?.[0];
  if (!runId) throw new Error(`No scripted run available for patient: ${patientId}`);
  return { run_id: runId };
}

export async function getRun(runId: string): Promise<RunSummary> {
  await randomDelay();
  const run = getStore().runsById.get(runId);
  if (!run) throw new Error(`Unknown run: ${runId}`);
  return run;
}

export async function validateBrief(
  briefId: string,
  validatedBy: string,
  edits?: Partial<MonitoringBrief>,
): Promise<MonitoringBrief> {
  await randomDelay();
  const store = getStore();
  const existing = store.briefsById.get(briefId);
  if (!existing) throw new Error(`Unknown brief: ${briefId}`);
  const updated: MonitoringBrief = {
    ...existing,
    ...edits,
    validated_by: validatedBy,
    validated_at: new Date().toISOString(),
  };
  store.briefsById.set(briefId, updated);
  store.latestBriefByPatient.set(updated.patient_id, updated);
  return updated;
}

export async function rejectBrief(
  briefId: string,
  validatedBy: string,
  reason: string,
): Promise<MonitoringBrief> {
  await randomDelay();
  const store = getStore();
  const existing = store.briefsById.get(briefId);
  if (!existing) throw new Error(`Unknown brief: ${briefId}`);
  const updated: MonitoringBrief = {
    ...existing,
    validated_by: validatedBy,
    validated_at: new Date().toISOString(),
    recommended_action: `${existing.recommended_action}\n\nRejected: ${reason}`,
  };
  store.briefsById.set(briefId, updated);
  store.latestBriefByPatient.set(updated.patient_id, updated);
  return updated;
}

export async function resetDemo(): Promise<{ ok: true }> {
  await randomDelay();
  resetStore();
  return { ok: true };
}
