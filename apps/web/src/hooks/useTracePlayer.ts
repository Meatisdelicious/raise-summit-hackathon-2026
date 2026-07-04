import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AgentEvent, MonitoringBrief } from "../types/contracts";

export type PlayerStatus = "idle" | "starting" | "playing" | "done" | "error";

// The reveal cadence. SSE can deliver every event in a single burst (replay mode) or trickle them
// over ~30 s (live Vultr). Either way, the player reveals ONE step at a time on this rhythm, so the
// UI always reads as "the agent is working" — never a wall of text that pops at once. When live
// events arrive slower than the cadence, the player simply waits (thinking) for the next one.
const STEP_INTERVAL_MS = 900; // minimum on-screen time before the next step reveals
const FIRST_STEP_MS = 500; // the initial "thinking" beat after the run starts

export interface TracePlayer {
  status: PlayerStatus;
  /** Events revealed so far, paced — not everything received over SSE yet. */
  visibleEvents: AgentEvent[];
  /** Set only when the `brief` step is actually REVEALED (the finale), never pre-loaded. */
  brief: MonitoringBrief | null;
  /** True while the player is waiting to reveal the next step (drives the "MILA is thinking" beat). */
  thinking: boolean;
  errorMessage: string | null;
  /** How many steps have been revealed (for a progress affordance). */
  revealedCount: number;
  start: () => Promise<void>;
  reset: () => void;
}

export function useTracePlayer(patientId: string): TracePlayer {
  const [status, setStatus] = useState<PlayerStatus>("idle");
  const [visibleEvents, setVisibleEvents] = useState<AgentEvent[]>([]);
  const [brief, setBrief] = useState<MonitoringBrief | null>(null);
  const [thinking, setThinking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Received-but-not-yet-revealed events, drained by the pump on a cadence.
  const queueRef = useRef<AgentEvent[]>([]);
  const closedRef = useRef(false); // the SSE stream signalled done/error
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unsubRef = useRef<(() => void) | null>(null);

  const clearTimers = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const reset = useCallback(() => {
    clearTimers();
    unsubRef.current?.();
    unsubRef.current = null;
    queueRef.current = [];
    closedRef.current = false;
    setStatus("idle");
    setVisibleEvents([]);
    setBrief(null);
    setThinking(false);
    setErrorMessage(null);
  }, []);

  // Reset whenever the patient changes; tear down on unmount.
  useEffect(() => {
    reset();
    return reset;
  }, [patientId, reset]);

  // The reveal pump: pop one queued event, show it, then schedule the next tick.
  const pump = useCallback(() => {
    const next = queueRef.current.shift();

    if (next) {
      setThinking(false);
      setVisibleEvents((prev) => [...prev, next]);

      if (next.type === "brief") setBrief(next.brief);
      if (next.type === "error") {
        setErrorMessage(next.message);
        setStatus("error");
        return; // stop the pump on error
      }
      if (next.type === "done") {
        setStatus("done");
        return; // the run's last frame — stop
      }
      timerRef.current = setTimeout(pump, STEP_INTERVAL_MS);
      return;
    }

    // Queue empty.
    if (closedRef.current) {
      setThinking(false);
      setStatus((s) => (s === "error" ? s : "done"));
      return;
    }
    // Still streaming — hold the "thinking" beat and poll again shortly.
    setThinking(true);
    timerRef.current = setTimeout(pump, 150);
  }, []);

  const start = useCallback(async () => {
    reset();
    setStatus("starting");
    setThinking(true);
    try {
      const { run_id } = await api.startRun(patientId);
      setStatus("playing");
      unsubRef.current = api.subscribeToRunEvents(run_id, {
        onEvent: (event) => {
          queueRef.current.push(event);
        },
        onDone: () => {
          closedRef.current = true;
        },
        onError: (message) => {
          queueRef.current.push({ type: "error", run_id, message });
          closedRef.current = true;
        },
      });
      clearTimers();
      timerRef.current = setTimeout(pump, FIRST_STEP_MS);
    } catch (err) {
      setStatus("error");
      setThinking(false);
      setErrorMessage(err instanceof Error ? err.message : "Failed to start the run.");
    }
  }, [patientId, pump, reset]);

  return {
    status,
    visibleEvents,
    brief,
    thinking,
    errorMessage,
    revealedCount: visibleEvents.length,
    start,
    reset,
  };
}
