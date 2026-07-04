import type { AgentEvent, HormoneResult, MonitoringBrief, Patient, RunSummary } from "../types/contracts";
import type { Api } from "./types";
import type { RunEventCallbacks } from "../mocks/server/eventStream";

// The real backend implementation. Unused while VITE_USE_MOCKS is true (the default). Base URL is
// a relative "/api" so it works via Vite's dev-server proxy (see vite.config.ts) or same-origin in
// production, without introducing a new required env var.
const BASE_URL = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

function subscribeToRunEvents(
  runId: string,
  { onEvent, onDone, onError }: RunEventCallbacks,
): () => void {
  const source = new EventSource(`${BASE_URL}/runs/${runId}/events`);

  source.onmessage = (message) => {
    try {
      const event = JSON.parse(message.data) as AgentEvent;
      onEvent(event);
      if (event.type === "done") {
        onDone();
        source.close();
        return;
      }
      if (event.type === "error") {
        // The backend publishes an ErrorEvent and then closes the bus, which would
        // otherwise trigger source.onerror and clobber this specific message with the
        // generic "connection lost" text. Close here so onerror can't fire.
        source.close();
        return;
      }
    } catch {
      onError("Failed to parse agent event.");
    }
  };

  source.onerror = () => {
    onError("Connection to the agent trace was lost.");
    source.close();
  };

  return () => source.close();
}

export const client: Api = {
  listPatients: () => request<Patient[]>("/patients"),
  getPatient: (id) => request<Patient>(`/patients/${id}`),
  getPatientResults: (id) => request<HormoneResult[]>(`/patients/${id}/results`),
  getLatestBrief: (id) => request<MonitoringBrief | null>(`/patients/${id}/latest-brief`),
  startRun: (patientId, resultId) =>
    request<{ run_id: string }>(`/patients/${patientId}/runs`, {
      method: "POST",
      body: JSON.stringify(resultId ? { result_id: resultId } : {}),
    }),
  getRun: (runId) => request<RunSummary>(`/runs/${runId}`),
  subscribeToRunEvents,
  validateBrief: (briefId, validatedBy, edits) =>
    request<MonitoringBrief>(`/briefs/${briefId}/validate`, {
      method: "POST",
      body: JSON.stringify({ validated_by: validatedBy, edits }),
    }),
  rejectBrief: (briefId, validatedBy, reason) =>
    request<MonitoringBrief>(`/briefs/${briefId}/reject`, {
      method: "POST",
      body: JSON.stringify({ validated_by: validatedBy, reason }),
    }),
  resetDemo: () => request<{ ok: true }>("/demo/reset", { method: "POST" }),
};
