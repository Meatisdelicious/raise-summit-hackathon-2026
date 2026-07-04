import type { AgentEvent } from "../../types/contracts";
import { getStore } from "./db";

export interface RunEventCallbacks {
  onEvent: (event: AgentEvent) => void;
  onDone: () => void;
  onError: (message: string) => void;
}

// Replays a scripted AgentEvent[] for a run_id, staggered like a real SSE stream. Returns an
// unsubscribe function. The real client (api/client.ts) wraps an actual EventSource behind this
// exact same signature, so callers (useAgentRun) never change when the backend goes live.
export function subscribeToRunEvents(
  runId: string,
  { onEvent, onDone, onError }: RunEventCallbacks,
): () => void {
  const events = getStore().eventsByRun.get(runId);
  if (!events) {
    onError(`No events found for run: ${runId}`);
    return () => {};
  }

  let cancelled = false;
  const timeouts: ReturnType<typeof setTimeout>[] = [];
  let elapsed = 0;

  for (const event of events) {
    const stepDelay = 400 + Math.random() * 500;
    elapsed += stepDelay;
    const timeoutId = setTimeout(() => {
      if (cancelled) return;
      onEvent(event);
      if (event.type === "done") onDone();
    }, elapsed);
    timeouts.push(timeoutId);
  }

  return () => {
    cancelled = true;
    for (const id of timeouts) clearTimeout(id);
  };
}
