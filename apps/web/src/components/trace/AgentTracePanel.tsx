import type { AgentEvent } from "../../types/contracts";
import { groupTraceEvents } from "../../lib/traceGrouping";
import { TraceEventItem } from "./TraceEventItem";

export function AgentTracePanel({ events }: { events: AgentEvent[] }) {
  const items = groupTraceEvents(events);

  if (items.length === 0) {
    return (
      <p className="trace-panel__empty">
        Run the review to watch MILA think — step by step, in real time.
      </p>
    );
  }

  return (
    <ol className="trace-timeline" aria-label="How MILA is thinking, step by step">
      {items.map((item, index) => (
        <TraceEventItem key={index} item={item} />
      ))}
    </ol>
  );
}
