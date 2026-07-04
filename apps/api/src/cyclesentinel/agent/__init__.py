"""The agent loop: plan, compute, conditional retrieval, branch, brief, escalate.

Public surface for the API lane: construct an :class:`AgentRunner` with a ``run_id``, an
:class:`~cyclesentinel.inference.base.LLMClient`, and a
:class:`~cyclesentinel.tools.ToolContext`, then iterate ``run(patient, result)`` to stream the
``AgentEvent`` trace. The pure decision helpers are exposed for reuse/testing.
"""

from __future__ import annotations

from cyclesentinel.agent.branch import branches_for
from cyclesentinel.agent.brief import draft_brief, is_grounded
from cyclesentinel.agent.limits import (
    AgentAmbiguousError,
    RetryPolicy,
    StepBudget,
    StepBudgetError,
)
from cyclesentinel.agent.loop import AgentRunner, baseline_stimulation_citation
from cyclesentinel.agent.planner import make_plan
from cyclesentinel.agent.prompts import brief_messages, plan_messages, run_query
from cyclesentinel.agent.state import (
    DEFAULT_MAX_GAP_DAYS,
    compute_monitoring_gap,
    decide_states,
    escalation_for,
    has_missing_timepoint,
)

__all__ = [
    "DEFAULT_MAX_GAP_DAYS",
    "AgentAmbiguousError",
    "AgentRunner",
    "RetryPolicy",
    "StepBudget",
    "StepBudgetError",
    "baseline_stimulation_citation",
    "branches_for",
    "brief_messages",
    "compute_monitoring_gap",
    "decide_states",
    "draft_brief",
    "escalation_for",
    "has_missing_timepoint",
    "is_grounded",
    "make_plan",
    "plan_messages",
    "run_query",
]
