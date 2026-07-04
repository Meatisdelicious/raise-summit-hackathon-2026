import type { ReactNode } from "react";
import type { AgentEvent, RuleType } from "../../types/contracts";
import type { TraceItem } from "../../lib/traceGrouping";
import type { Tone } from "../../lib/decisionLabels";
import { signalLabel } from "../../lib/glossary";
import { CheckIcon, ChevronIcon, InfoIcon, WarningIcon, DotIcon } from "../shared/icons";

const ruleTypeLabel: Record<RuleType, string> = {
  ohss: "over-response (OHSS)",
  luteinization: "early maturation",
  poor_responder: "slow response",
  stimulation: "stimulation",
};

function toneIcon(tone: Tone) {
  switch (tone) {
    case "danger":
    case "warning":
      return WarningIcon;
    case "success":
      return CheckIcon;
    case "info":
      return InfoIcon;
    default:
      return DotIcon;
  }
}

interface StepDescriptor {
  tone: Tone | "primary";
  eyebrow: string;
  title: string;
  body?: ReactNode;
  evidence?: ReactNode;
  plan?: string[];
  isError?: boolean;
}

function describe(event: AgentEvent): StepDescriptor {
  switch (event.type) {
    case "plan":
      return {
        tone: "info",
        eyebrow: "Plan",
        title: "MILA drafted a plan",
        plan: event.plan,
      };
    case "retrieve":
      return {
        tone: "info",
        eyebrow: "Gather",
        title: event.what === "patient_context" ? "Read the patient's context" : "Read the hormone trajectory",
        body: event.summary,
      };
    case "compute": {
      const { friendly } = signalLabel(event.signal.name);
      return {
        tone: event.signal.tripped ? "warning" : "success",
        eyebrow: "Measure",
        title: friendly,
        body: (
          <>
            <strong>{event.signal.tripped ? "Tripped" : "Clear"}</strong> · {event.signal.detail}
          </>
        ),
        evidence: `${event.signal.name} = ${event.signal.value}`,
      };
    }
    case "branch":
      return {
        tone: "primary",
        eyebrow: "Decision",
        title: "MILA decided to look deeper",
        body: event.reason,
      };
    case "retrieve_rule":
      return {
        tone: "primary",
        eyebrow: "Protocol",
        title: "Opened a specific protocol rule",
        body: `MILA pulled the exact protocol page for the ${ruleTypeLabel[event.rule_type]} rule.`,
        evidence: `${event.citation.article} · page ${event.citation.page} · score ${event.citation.score?.toFixed(2)}`,
      };
    case "action":
      return {
        tone: "info",
        eyebrow: "Action",
        title: event.name === "dose_adjustment" ? "Suggested a dose adjustment" : "Suggested next check timing",
        body: event.detail,
      };
    case "brief":
      return {
        tone: "success",
        eyebrow: "Brief",
        title: "Drafted the monitoring brief",
        body: "MILA's read is on the right — flags, interpretation and the exact protocol lines it cited.",
      };
    case "escalate":
      return {
        tone: event.level === "urgent" ? "danger" : "warning",
        eyebrow: "Escalate",
        title: "Flagged for review",
        body: `Flagged for the ${event.to} to review — nothing is sent to the patient.`,
      };
    case "error":
      return {
        tone: "danger",
        eyebrow: "Error",
        title: "The run hit a problem",
        body: event.message,
        isError: true,
      };
    case "done":
      return {
        tone: "success",
        eyebrow: "Done",
        title: "Review complete",
      };
  }
}

function Step({ event }: { event: AgentEvent }) {
  const d = describe(event);
  const Icon = d.tone === "primary" ? ChevronIcon : toneIcon(d.tone as Tone);

  return (
    <li className={`trace-step trace-step--${d.tone}`}>
      <span className="trace-step__rail" aria-hidden="true">
        <span className="trace-step__dot">
          <Icon />
        </span>
      </span>
      <div className="trace-step__body" {...(d.isError ? { role: "alert" } : {})}>
        <p className="trace-step__eyebrow">{d.eyebrow}</p>
        <p className="trace-step__title">{d.title}</p>
        {d.body && <p className="trace-step__body-text">{d.body}</p>}
        {d.plan && (
          <ol className="trace-step__plan">
            {d.plan.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ol>
        )}
        {d.evidence && <p className="trace-step__evidence">{d.evidence}</p>}
      </div>
    </li>
  );
}

export function TraceEventItem({ item }: { item: TraceItem }) {
  if (item.kind === "single") {
    return <Step event={item.event} />;
  }

  const { branch, retrieveRule } = item;
  return (
    <li className="trace-step trace-step--primary trace-step--pair">
      <span className="trace-step__rail" aria-hidden="true">
        <span className="trace-step__dot">
          <ChevronIcon />
        </span>
      </span>
      <div className="trace-step__body">
        <div className="trace-pair">
          <p className="trace-pair__eyebrow">Why it looked deeper</p>
          <p className="trace-pair__reason">{branch.reason}</p>
          <p className="trace-pair__rule">
            Fetched the <strong>{ruleTypeLabel[retrieveRule.rule_type]}</strong> rule —{" "}
            {retrieveRule.citation.article} (page {retrieveRule.citation.page}, score{" "}
            {retrieveRule.citation.score?.toFixed(2)})
          </p>
          {retrieveRule.hits.length > 0 && (
            <ul className="trace-item__hits">
              {retrieveRule.hits.map((hit) => {
                const chosen =
                  hit.doc_id === retrieveRule.citation.doc_id && hit.page === retrieveRule.citation.page;
                return (
                  <li
                    key={`${hit.doc_id}-${hit.page}`}
                    className={chosen ? "trace-item__hit trace-item__hit--chosen" : "trace-item__hit"}
                  >
                    {hit.doc_id} p{hit.page} · {hit.article} · score {hit.score.toFixed(2)}
                    {chosen ? " ✓" : ""}
                  </li>
                );
              })}
            </ul>
          )}
          <p className="trace-pair__caption">
            It went back for the exact protocol rule <em>because of what it just measured</em> —
            that's what makes MILA an agent, not a search box.
          </p>
        </div>
      </div>
    </li>
  );
}
