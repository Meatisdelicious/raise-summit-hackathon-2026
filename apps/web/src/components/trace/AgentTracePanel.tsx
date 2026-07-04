import type { AgentEvent } from "../../types/contracts";
import { groupTraceEvents } from "../../lib/traceGrouping";
import { TraceEventItem } from "./TraceEventItem";

export function AgentTracePanel({ events }: { events: AgentEvent[] }) {
  const items = groupTraceEvents(events);

  if (items.length === 0) {
    return <p className="trace-panel__empty">Run the monitoring review to see the agent's trace.</p>;
  }

  return (
    <ol className="trace-panel" aria-label="Live agent trace">
      {items.map((item, index) => (
        <li key={index}>
          <TraceEventItem item={item} />
        </li>
      ))}
    </ol>
  );
}
