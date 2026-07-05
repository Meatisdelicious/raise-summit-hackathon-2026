"""Brief tools: ``create_monitoring_brief`` and ``escalate_to_biologist``.

``create_monitoring_brief`` assembles the cited :class:`MonitoringBrief` object (deterministic id +
timestamp from ``ctx``); it does not persist — the agent/API lane owns the write. It always leaves
``validated_by``/``validated_at`` unset: a human validates before the brief reaches the clinic
(``docs/safety.md``). ``escalate_to_biologist`` records the escalation level and that human
validation is required.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from cyclesentinel.enums import DecisionState, EscalationLevel
from cyclesentinel.schemas import Citation, MonitoringBrief
from cyclesentinel.tools.base import ToolContext, make_tool, register


class CreateMonitoringBriefArgs(BaseModel):
    """Arguments for ``create_monitoring_brief`` (everything needed to assemble the cited brief)."""

    patient_id: str
    result_id: str
    run_id: str
    states: list[DecisionState]
    interpretation: str
    recommended_action: str
    citations: list[Citation] = Field(default_factory=list)
    escalation_level: EscalationLevel = EscalationLevel.NONE


class EscalateToBiologistArgs(BaseModel):
    """Arguments for ``escalate_to_biologist``."""

    level: EscalationLevel
    to: str = "biologist"
    reason: str = ""


class EscalationResult(BaseModel):
    """The recorded escalation: level, recipient, and that a human must validate first."""

    level: EscalationLevel
    to: str
    requires_human_validation: bool
    detail: str


async def _create_monitoring_brief(
    ctx: ToolContext, args: CreateMonitoringBriefArgs
) -> MonitoringBrief:
    return MonitoringBrief(
        id=ctx.ids.next("brief"),
        patient_id=args.patient_id,
        result_id=args.result_id,
        run_id=args.run_id,
        states=args.states,
        interpretation=args.interpretation,
        recommended_action=args.recommended_action,
        citations=args.citations,
        escalation_level=args.escalation_level,
        validated_by=None,
        validated_at=None,
        created_at=ctx.clock.now(),
    )


async def _escalate_to_biologist(
    ctx: ToolContext, args: EscalateToBiologistArgs
) -> EscalationResult:
    reason = f": {args.reason}" if args.reason else ""
    return EscalationResult(
        level=args.level,
        to=args.to,
        requires_human_validation=True,
        detail=f"escalation '{args.level}' routed to {args.to}{reason}; awaiting human validation",
    )


create_monitoring_brief = register(
    make_tool(
        name="create_monitoring_brief",
        description=(
            "Assemble the cited monitoring brief (states, interpretation, recommended action, "
            "citations, escalation level) for human validation. Does not validate or send it."
        ),
        args_model=CreateMonitoringBriefArgs,
        result_model=MonitoringBrief,
        fn=_create_monitoring_brief,
    )
)

escalate_to_biologist = register(
    make_tool(
        name="escalate_to_biologist",
        description=(
            "Attach an escalation level (none | info | urgent) and record that human validation by "
            "a biologist is required before the brief reaches the clinic."
        ),
        args_model=EscalateToBiologistArgs,
        result_model=EscalationResult,
        fn=_escalate_to_biologist,
    )
)
