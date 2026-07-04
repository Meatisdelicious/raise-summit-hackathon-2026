"""Pure decision logic: computed signals + trajectory -> decision states + escalation level.

:func:`decide_states` is deterministic and fail-safe: any escalating trip removes
``ROUTINE_CONTINUE`` from the result (a run that should escalate can never resolve to routine), and
a run may raise more than one flag (the killer case = OHSS + luteinization).
:func:`compute_monitoring_gap` is the sixth "signal" — a compute-phase check (not a registered
tool) that surfaces a missing monitoring draw.
"""

from __future__ import annotations

from collections.abc import Sequence

from cyclesentinel.enums import DecisionState, EscalationLevel
from cyclesentinel.schemas import ComputedSignal, HormoneResult

# Monitoring cadence: draws more than this many cycle days apart imply a skipped timepoint.
# Mirrors ``data/synthetic/thresholds.json`` next_draw_timing.max_gap_days_before_missing.
DEFAULT_MAX_GAP_DAYS = 2


def _tripped(signals: Sequence[ComputedSignal], name: str) -> bool:
    return any(s.name == name and s.tripped for s in signals)


def compute_monitoring_gap(
    trajectory: Sequence[HormoneResult], max_gap_days: int = DEFAULT_MAX_GAP_DAYS
) -> ComputedSignal:
    """The widest cycle-day gap between consecutive draws; trips when it exceeds the cadence.

    ``value`` is the gap in days. It **trips** when a scheduled monitoring draw was skipped — the
    signal that drives ``MISSING_TIMEPOINT``.
    """
    pts = sorted(trajectory, key=lambda r: r.cycle_day)
    widest = 0
    span = "single draw"
    for prev, curr in zip(pts, pts[1:], strict=False):
        gap = curr.cycle_day - prev.cycle_day
        if gap > widest:
            widest = gap
            span = f"day {prev.cycle_day} -> day {curr.cycle_day}"
    tripped = widest > max_gap_days
    detail = (
        f"{widest}-day gap ({span}) exceeds the {max_gap_days}-day monitoring cadence"
        if tripped
        else f"widest gap {widest}d within the {max_gap_days}-day monitoring cadence"
    )
    return ComputedSignal(name="monitoring_gap", value=widest, detail=detail, tripped=tripped)


def has_missing_timepoint(
    trajectory: Sequence[HormoneResult], max_gap_days: int = DEFAULT_MAX_GAP_DAYS
) -> bool:
    """True if any consecutive-draw cycle-day gap exceeds the monitoring cadence."""
    return compute_monitoring_gap(trajectory, max_gap_days).tripped


def decide_states(
    signals: Sequence[ComputedSignal],
    retrievals: Sequence[object],
    trajectory: Sequence[HormoneResult],
) -> list[DecisionState]:
    """Resolve the constrained decision states from the tripped signals and trajectory.

    Fail-safe: ``ROUTINE_CONTINUE`` is returned only when *nothing* flags, so any escalating trip
    (OHSS, luteinization, poor response, missing timepoint) guarantees the result never contains
    ``ROUTINE_CONTINUE``. ``retrievals`` is accepted for symmetry with the loop (the states are
    decided by computation, not by what was retrieved).
    """
    # ``retrievals`` is intentionally not consulted: states are computation-driven.
    states: list[DecisionState] = []
    if _tripped(signals, "ohss_composite"):
        states.append(DecisionState.OHSS_RISK_ESCALATE)
    if _tripped(signals, "progesterone_for_day"):
        states.append(DecisionState.PREMATURE_LUTEINIZATION_FLAG)
    if _tripped(signals, "response_curve"):
        states.append(DecisionState.POOR_RESPONSE_FLAG)
    if _tripped(signals, "monitoring_gap") or has_missing_timepoint(trajectory):
        states.append(DecisionState.MISSING_TIMEPOINT)
    if not states:
        states.append(DecisionState.ROUTINE_CONTINUE)
    return states


def escalation_for(states: Sequence[DecisionState]) -> EscalationLevel:
    """Map the decision states to an escalation level (urgent > info > none)."""
    urgent = {
        DecisionState.OHSS_RISK_ESCALATE,
        DecisionState.PREMATURE_LUTEINIZATION_FLAG,
        DecisionState.AMBIGUOUS_REQUIRES_REVIEW,
    }
    info = {DecisionState.POOR_RESPONSE_FLAG, DecisionState.MISSING_TIMEPOINT}
    if any(s in urgent for s in states):
        return EscalationLevel.URGENT
    if any(s in info for s in states):
        return EscalationLevel.INFO
    return EscalationLevel.NONE
