"""The SSE agent-trace event union — mirrors ``docs/CONTRACTS.md`` §4 byte-for-byte.

Each event is a Pydantic model with a ``Literal`` ``type`` discriminator. ``AgentEvent`` is the
tagged union the ``GET /api/runs/{run_id}/events`` endpoint streams; :func:`sse_format` renders one
event as a single ``data: <json>\\n\\n`` SSE frame with compact JSON.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

from cyclesentinel.enums import DecisionState, EscalationLevel, RuleType
from cyclesentinel.schemas import Citation, ComputedSignal, MonitoringBrief, RetrievalHit


class PlanEvent(BaseModel):
    """The agent announces its plan for interpreting the new result."""

    type: Literal["plan"] = "plan"
    run_id: str
    step: int
    plan: list[str]


class RetrieveEvent(BaseModel):
    """The agent fetches patient context or the trajectory (unconditional, deterministic)."""

    type: Literal["retrieve"] = "retrieve"
    run_id: str
    step: int
    what: Literal["patient_context", "trajectory"]
    summary: str


class ComputeEvent(BaseModel):
    """The agent runs a deterministic calculator and emits its computed signal."""

    type: Literal["compute"] = "compute"
    run_id: str
    step: int
    signal: ComputedSignal


class BranchEvent(BaseModel):
    """A computed signal tripped — the agent is about to retrieve a governing rule."""

    type: Literal["branch"] = "branch"
    run_id: str
    step: int
    reason: str
    rule_type: RuleType


class RetrieveRuleEvent(BaseModel):
    """Conditional visual document retrieval (Prime-8B): pages + scores + chosen citation."""

    type: Literal["retrieve_rule"] = "retrieve_rule"
    run_id: str
    step: int
    rule_type: RuleType
    hits: list[RetrievalHit]
    citation: Citation


class ActionEvent(BaseModel):
    """The agent computes a dose adjustment or the next-draw timing."""

    type: Literal["action"] = "action"
    run_id: str
    step: int
    name: Literal["dose_adjustment", "next_draw_timing"]
    detail: str


class BriefEvent(BaseModel):
    """The assembled, cited monitoring brief."""

    type: Literal["brief"] = "brief"
    run_id: str
    step: int
    brief: MonitoringBrief


class EscalateEvent(BaseModel):
    """An escalation flag is attached; a human must validate."""

    type: Literal["escalate"] = "escalate"
    run_id: str
    step: int
    level: EscalationLevel
    to: str


class ErrorEvent(BaseModel):
    """A terminal error in the run."""

    type: Literal["error"] = "error"
    run_id: str
    message: str


class DoneEvent(BaseModel):
    """The run finished; carries the final decision states."""

    type: Literal["done"] = "done"
    run_id: str
    final_states: list[DecisionState]


AgentEvent = Annotated[
    PlanEvent
    | RetrieveEvent
    | ComputeEvent
    | BranchEvent
    | RetrieveRuleEvent
    | ActionEvent
    | BriefEvent
    | EscalateEvent
    | ErrorEvent
    | DoneEvent,
    Field(discriminator="type"),
]

agent_event_adapter: TypeAdapter[AgentEvent] = TypeAdapter(AgentEvent)


def sse_format(event: AgentEvent) -> bytes:
    """Render an :data:`AgentEvent` as a single SSE frame: ``data: <compact-json>\\n\\n``."""
    payload = agent_event_adapter.dump_json(event)
    return b"data: " + payload + b"\n\n"
