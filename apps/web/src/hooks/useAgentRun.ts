import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AgentEvent, MonitoringBrief } from "../types/contracts";

export type RunStatus = "idle" | "starting" | "running" | "done" | "error";

export function useAgentRun(patientId: string): {
  status: RunStatus;
  events: AgentEvent[];
  brief: MonitoringBrief | null;
  errorMessage: string | null;
  start: () => Promise<void>;
} {
  const [status, setStatus] = useState<RunStatus>("idle");
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [brief, setBrief] = useState<MonitoringBrief | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  // Reset the run when navigating to a different patient.
  useEffect(() => {
    setStatus("idle");
    setEvents([]);
    setBrief(null);
    setErrorMessage(null);
    return () => {
      unsubscribeRef.current?.();
      unsubscribeRef.current = null;
    };
  }, [patientId]);

  const start = useCallback(async () => {
    unsubscribeRef.current?.();
    setStatus("starting");
    setEvents([]);
    setBrief(null);
    setErrorMessage(null);

    try {
      const { run_id } = await api.startRun(patientId);
      setStatus("running");
      unsubscribeRef.current = api.subscribeToRunEvents(run_id, {
        onEvent: (event) => {
          setEvents((prev) => [...prev, event]);
          if (event.type === "brief") setBrief(event.brief);
          if (event.type === "error") {
            setStatus("error");
            setErrorMessage(event.message);
          }
        },
        onDone: () => setStatus("done"),
        onError: (message) => {
          setStatus("error");
          setErrorMessage(message);
        },
      });
    } catch (err) {
      setStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "Failed to start the run.");
    }
  }, [patientId]);

  return { status, events, brief, errorMessage, start };
}
