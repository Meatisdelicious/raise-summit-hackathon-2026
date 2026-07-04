import type { AgentEvent } from "../../types/contracts";
import { groupTraceEvents, type TraceItem } from "../../lib/traceGrouping";
import { TraceEventItem } from "./TraceEventItem";

// Stable identity per rendered row so React keeps existing steps mounted (they don't re-animate)
// while a newly revealed step mounts fresh and plays its entrance. The branch→retrieve_rule pair
// gets its own key so the moment it forms it remounts and plays the spotlight.
function itemKey(item: TraceItem): string {
  if (item.kind === "single") {
    const e = item.event;
    return "step" in e ? `s-${e.type}-${e.step}` : `s-${e.type}`;
  }
  return `p-${item.branch.step}`;
}

export function AgentTracePanel({
  events,
  thinking,
  running,
}: {
  events: AgentEvent[];
  thinking: boolean;
  running: boolean;
}) {
  const items = groupTraceEvents(events);

  return (
    <ol className="trace-timeline" aria-label="How MILA is thinking, step by step">
      {items.map((item) => (
        <TraceEventItem key={itemKey(item)} item={item} />
      ))}
      {running && thinking && (
        <li className="trace-step trace-step--thinking" aria-hidden="true">
          <span className="trace-step__rail">
            <span className="trace-step__dot trace-step__dot--pulse" />
          </span>
          <div className="trace-step__body">
            <p className="trace-thinking__label">MILA is thinking…</p>
          </div>
        </li>
      )}
    </ol>
  );
}
