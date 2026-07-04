import type { AgentEvent } from "../../types/contracts";
import type { TraceItem } from "../../lib/traceGrouping";
import { CheckIcon, ChevronIcon, InfoIcon, WarningIcon } from "../shared/icons";

function SingleEvent({ event }: { event: AgentEvent }) {
  switch (event.type) {
    case "plan":
      return (
        <div className="trace-item trace-item--plan">
          <InfoIcon />
          <div>
            <strong>Plan created.</strong>
            <ol>
              {event.plan.map((step, index) => (
                <li key={index}>{step}</li>
              ))}
            </ol>
          </div>
        </div>
      );
    case "retrieve":
      return (
        <div className="trace-item">
          <InfoIcon />
          <span>
            Retrieved {event.what === "patient_context" ? "patient context" : "trajectory"}:{" "}
            {event.summary}
          </span>
        </div>
      );
    case "compute":
      return (
        <div className="trace-item">
          {event.signal.tripped ? <WarningIcon /> : <CheckIcon />}
          <span>
            <strong>{event.signal.name}:</strong> {event.signal.detail}
          </span>
        </div>
      );
    case "branch":
      return (
        <div className="trace-item">
          <ChevronIcon />
          <span>Branch: {event.reason}</span>
        </div>
      );
    case "retrieve_rule":
      return (
        <div className="trace-item">
          <InfoIcon />
          <span>
            Retrieved {event.rule_type} rule — {event.citation.article} (score{" "}
            {event.citation.score?.toFixed(2)})
          </span>
        </div>
      );
    case "action":
      return (
        <div className="trace-item">
          <InfoIcon />
          <span>
            <strong>Next action:</strong> {event.detail}
          </span>
        </div>
      );
    case "brief":
      return (
        <div className="trace-item">
          <CheckIcon />
          <span>Monitoring brief drafted — see the evidence panel below.</span>
        </div>
      );
    case "escalate":
      return (
        <div className="trace-item">
          <WarningIcon />
          <span>
            Escalated ({event.level}) to the {event.to}.
          </span>
        </div>
      );
    case "error":
      return (
        <div className="trace-item trace-item--error" role="alert">
          <WarningIcon />
          <span>{event.message}</span>
        </div>
      );
    case "done":
      return (
        <div className="trace-item">
          <CheckIcon />
          <span>Run complete.</span>
        </div>
      );
  }
}

export function TraceEventItem({ item }: { item: TraceItem }) {
  if (item.kind === "single") {
    return <SingleEvent event={item.event} />;
  }

  const { branch, retrieveRule } = item;
  return (
    <div className="trace-item trace-item--pair">
      <div className="trace-item__why">
        <ChevronIcon />
        <span>{branch.reason}</span>
      </div>
      <div className="trace-item__connector" aria-hidden="true" />
      <div className="trace-item__what">
        <WarningIcon />
        <span>
          Fetched the <strong>{retrieveRule.rule_type}</strong> rule — {retrieveRule.citation.article}{" "}
          (page {retrieveRule.citation.page}, score {retrieveRule.citation.score?.toFixed(2)})
        </span>
      </div>
    </div>
  );
}
