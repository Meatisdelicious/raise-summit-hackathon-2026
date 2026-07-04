"""A deterministic, in-process agent runner that reproduces the frozen demo traces.

The real agent loop is a separate lane; the API lane owns only the plumbing (bus, persistence,
SSE). This scripted runner emits the exact golden event sequences from ``docs/doc.md`` §7 so the
API tests can assert trace order, the routine (R) no-branch invariant, brief persistence, and
SSE framing without depending on the loop lane's delivery.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from cyclesentinel.api.deps import AgentRunner
from cyclesentinel.enums import DecisionState, EscalationLevel, RuleType
from cyclesentinel.events import (
    ActionEvent,
    AgentEvent,
    BranchEvent,
    BriefEvent,
    ComputeEvent,
    DoneEvent,
    EscalateEvent,
    PlanEvent,
    RetrieveEvent,
    RetrieveRuleEvent,
)
from cyclesentinel.schemas import Citation, ComputedSignal, MonitoringBrief, RetrievalHit

# The frozen type order for the killer case K (branch -> retrieve_rule pairs are the money shot).
GOLDEN_K_TYPES: tuple[str, ...] = (
    "plan",
    "retrieve",
    "retrieve",
    "compute",
    "compute",
    "compute",
    "branch",
    "retrieve_rule",
    "compute",
    "branch",
    "retrieve_rule",
    "action",
    "brief",
    "escalate",
    "done",
)

# The routine case R: computes but NO branch / NO retrieve_rule (retrievals are computation-driven).
GOLDEN_R_TYPES: tuple[str, ...] = (
    "plan",
    "retrieve",
    "retrieve",
    "compute",
    "compute",
    "compute",
    "compute",
    "action",
    "brief",
    "done",
)

_CREATED_AT = datetime(2026, 6, 27, 9, 0, tzinfo=UTC)


def _signal(name: str, value: float | str, detail: str, tripped: bool) -> ComputedSignal:
    return ComputedSignal(name=name, value=value, detail=detail, tripped=tripped)


def _hit(rule_type: RuleType, doc_id: str, page: int, article: str) -> RetrievalHit:
    return RetrievalHit(
        doc_id=doc_id,
        rule_type=rule_type,
        page=page,
        score=0.91,
        text=f"{article} governing rule text layer.",
        article=article,
    )


def _citation(rule_type: RuleType, doc_id: str, page: int, article: str, quote: str) -> Citation:
    return Citation(
        doc_id=doc_id, rule_type=rule_type, page=page, article=article, quote=quote, score=0.91
    )


def _killer_events(run_id: str, patient_id: str, result_id: str) -> list[AgentEvent]:
    ohss_cite = _citation("ohss", "ohss_sop", 4, "§4.2", "Coast or trigger-swap when E2 > 4000.")
    lut_cite = _citation(
        "luteinization", "luteinization_rule", 2, "§2.1", "P4 > 1.5 on day 8 → consider freeze-all."
    )
    brief = MonitoringBrief(
        id="brief-K",
        patient_id=patient_id,
        result_id=result_id,
        run_id=run_id,
        states=[DecisionState.OHSS_RISK_ESCALATE, DecisionState.PREMATURE_LUTEINIZATION_FLAG],
        interpretation="Steep E2 rise with borderline P4 for day 8; OHSS + luteinization risk.",
        recommended_action="Escalate to biologist; consider coasting and freeze-all per SOP.",
        citations=[ohss_cite, lut_cite],
        escalation_level=EscalationLevel.URGENT,
        created_at=_CREATED_AT,
    )
    return [
        PlanEvent(run_id=run_id, step=1, plan=["context", "trajectory", "compute", "decide"]),
        RetrieveEvent(run_id=run_id, step=2, what="patient_context", summary="antagonist, PCOS"),
        RetrieveEvent(run_id=run_id, step=3, what="trajectory", summary="4 draws, days 3-8"),
        ComputeEvent(run_id=run_id, step=4, signal=_signal("e2_rate", 61.5, "E2 +62%/day", True)),
        ComputeEvent(
            run_id=run_id, step=5, signal=_signal("e2_per_follicle", 221.0, "221 pg/foll", False)
        ),
        ComputeEvent(
            run_id=run_id, step=6, signal=_signal("ohss_composite", "high", "OHSS high", True)
        ),
        BranchEvent(run_id=run_id, step=7, reason="OHSS composite tripped", rule_type="ohss"),
        RetrieveRuleEvent(
            run_id=run_id,
            step=8,
            rule_type="ohss",
            hits=[_hit("ohss", "ohss_sop", 4, "§4.2")],
            citation=ohss_cite,
        ),
        ComputeEvent(
            run_id=run_id,
            step=9,
            signal=_signal("progesterone_for_day", 1.6, "P4 1.6 > 1.5 (day 8)", True),
        ),
        BranchEvent(run_id=run_id, step=10, reason="P4 high for day 8", rule_type="luteinization"),
        RetrieveRuleEvent(
            run_id=run_id,
            step=11,
            rule_type="luteinization",
            hits=[_hit("luteinization", "luteinization_rule", 2, "§2.1")],
            citation=lut_cite,
        ),
        ActionEvent(run_id=run_id, step=12, name="next_draw_timing", detail="next draw in 24h"),
        BriefEvent(run_id=run_id, step=13, brief=brief),
        EscalateEvent(run_id=run_id, step=14, level=EscalationLevel.URGENT, to="biologist"),
        DoneEvent(
            run_id=run_id,
            final_states=[
                DecisionState.OHSS_RISK_ESCALATE,
                DecisionState.PREMATURE_LUTEINIZATION_FLAG,
            ],
        ),
    ]


def _routine_events(run_id: str, patient_id: str, result_id: str) -> list[AgentEvent]:
    brief = MonitoringBrief(
        id="brief-R",
        patient_id=patient_id,
        result_id=result_id,
        run_id=run_id,
        states=[DecisionState.ROUTINE_CONTINUE],
        interpretation="Trajectory within expected bounds for day 8.",
        recommended_action="Continue protocol; standard next draw.",
        citations=[],
        escalation_level=EscalationLevel.NONE,
        created_at=_CREATED_AT,
    )
    return [
        PlanEvent(run_id=run_id, step=1, plan=["context", "trajectory", "compute", "decide"]),
        RetrieveEvent(run_id=run_id, step=2, what="patient_context", summary="antagonist"),
        RetrieveEvent(run_id=run_id, step=3, what="trajectory", summary="4 draws, days 3-8"),
        ComputeEvent(run_id=run_id, step=4, signal=_signal("e2_rate", 37.8, "E2 +38%/day", False)),
        ComputeEvent(
            run_id=run_id, step=5, signal=_signal("e2_per_follicle", 168.0, "168 pg/foll", False)
        ),
        ComputeEvent(
            run_id=run_id, step=6, signal=_signal("ohss_composite", "low", "OHSS low", False)
        ),
        ComputeEvent(
            run_id=run_id, step=7, signal=_signal("progesterone_for_day", 0.9, "P4 normal", False)
        ),
        ActionEvent(run_id=run_id, step=8, name="next_draw_timing", detail="next draw in 48h"),
        BriefEvent(run_id=run_id, step=9, brief=brief),
        DoneEvent(run_id=run_id, final_states=[DecisionState.ROUTINE_CONTINUE]),
    ]


class ScriptedRunner:
    """Emits the frozen K / R traces, selected by patient id (default = killer)."""

    async def run(self, run_id: str, patient_id: str, result_id: str) -> AsyncIterator[AgentEvent]:
        if patient_id == "pat-R":
            events = _routine_events(run_id, patient_id, result_id)
        else:
            events = _killer_events(run_id, patient_id, result_id)
        for event in events:
            await asyncio.sleep(0)  # yield so a live SSE subscriber interleaves
            yield event


def scripted_factory(session: Session) -> AgentRunner:
    """A :class:`~cyclesentinel.api.deps.RunnerFactory` that returns a :class:`ScriptedRunner`."""
    return ScriptedRunner()
