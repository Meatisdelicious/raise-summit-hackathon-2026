import type { AgentEvent } from "../types/contracts";

type BranchEvent = Extract<AgentEvent, { type: "branch" }>;
type RetrieveRuleEvent = Extract<AgentEvent, { type: "retrieve_rule" }>;

export type TraceItem =
  | { kind: "single"; event: AgentEvent }
  | { kind: "branch_retrieve_pair"; branch: BranchEvent; retrieveRule: RetrieveRuleEvent };

// Pairs a `branch` event with the `retrieve_rule` that immediately follows it for the same
// rule_type into one visual unit — the "why" next to the "what came back". This is the single
// place the pairing rule lives, independent of how it's rendered. A patient whose fixture has no
// branch/retrieve_rule events (the routine control case) simply produces zero pairs here.
export function groupTraceEvents(events: AgentEvent[]): TraceItem[] {
  const items: TraceItem[] = [];

  for (let i = 0; i < events.length; i++) {
    const event = events[i];
    const next = events[i + 1];

    if (event.type === "branch" && next?.type === "retrieve_rule" && next.rule_type === event.rule_type) {
      items.push({ kind: "branch_retrieve_pair", branch: event, retrieveRule: next });
      i++; // consume the paired retrieve_rule event too
      continue;
    }

    items.push({ kind: "single", event });
  }

  return items;
}
