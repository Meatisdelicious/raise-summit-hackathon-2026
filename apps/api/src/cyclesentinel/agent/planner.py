"""The planning turn: ask the LLM for an ordered triage plan and schema-validate it.

The LLM returns a JSON object ``{"plan": ["step", ...]}``; :func:`make_plan` parses and validates it
(a non-empty list of strings), retrying once per :class:`RetryPolicy` before raising
:class:`AgentAmbiguousError`. The plan is narrative for the trace — the actual tool sequence is
deterministic — so a malformed plan degrades the run to review rather than guessing.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from cyclesentinel.agent.limits import AgentAmbiguousError, RetryPolicy
from cyclesentinel.agent.prompts import plan_messages, run_query
from cyclesentinel.inference.base import ChatResponse, LLMClient
from cyclesentinel.schemas import HormoneResult, Patient


def _parse_plan(resp: ChatResponse) -> list[str] | None:
    """Extract a non-empty ``list[str]`` plan from the LLM response, or ``None`` if malformed."""
    content = resp.content
    if not content:
        return None
    try:
        data: object = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    plan = data.get("plan")
    if not isinstance(plan, list):
        return None
    steps = [item for item in plan if isinstance(item, str) and item.strip()]
    return steps or None


async def make_plan(
    llm: LLMClient,
    patient: Patient,
    results: Sequence[HormoneResult],
    *,
    policy: RetryPolicy | None = None,
) -> list[str]:
    """Return the LLM's ordered triage plan, retrying once on invalid output then AMBIGUOUS."""
    policy = policy or RetryPolicy()
    messages = plan_messages(run_query(patient, results))
    for _ in range(policy.attempts):
        plan = _parse_plan(await llm.chat(messages))
        if plan is not None:
            return plan
    raise AgentAmbiguousError("planner: model did not return a valid plan")
