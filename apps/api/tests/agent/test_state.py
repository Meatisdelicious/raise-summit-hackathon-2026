"""``decide_states`` / ``escalation_for`` — pure decision logic and the fail-safe."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cyclesentinel.agent import compute_monitoring_gap, decide_states, escalation_for
from cyclesentinel.enums import DecisionState, EscalationLevel
from cyclesentinel.schemas import ComputedSignal, HormoneResult

_BASE = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)


def _sig(name: str, *, tripped: bool) -> ComputedSignal:
    return ComputedSignal(name=name, value=0.0, detail="", tripped=tripped)


def _draw(cycle_day: int) -> HormoneResult:
    return HormoneResult(
        id=f"r{cycle_day}",
        patient_id="p",
        cycle_day=cycle_day,
        drawn_at=_BASE + timedelta(days=cycle_day),
        e2=1000.0,
        lh=2.0,
        progesterone=0.8,
    )


_DENSE = [_draw(3), _draw(5), _draw(7), _draw(8)]  # no gap > 2 days


def test_nothing_trips_is_routine() -> None:
    signals = [_sig("ohss_composite", tripped=False), _sig("response_curve", tripped=False)]
    assert decide_states(signals, [], _DENSE) == [DecisionState.ROUTINE_CONTINUE]


def test_dual_flag_killer_case() -> None:
    signals = [_sig("ohss_composite", tripped=True), _sig("progesterone_for_day", tripped=True)]
    states = decide_states(signals, [], _DENSE)
    assert states == [
        DecisionState.OHSS_RISK_ESCALATE,
        DecisionState.PREMATURE_LUTEINIZATION_FLAG,
    ]


def test_fail_safe_escalating_trip_never_routine() -> None:
    for name in ("ohss_composite", "progesterone_for_day", "response_curve"):
        states = decide_states([_sig(name, tripped=True)], [], _DENSE)
        assert DecisionState.ROUTINE_CONTINUE not in states
        assert states  # never silently empty


def test_missing_timepoint_detected_from_trajectory_gap() -> None:
    sparse = [_draw(3), _draw(5), _draw(8)]  # day-7 draw absent -> 3-day gap
    states = decide_states([_sig("ohss_composite", tripped=False)], [], sparse)
    assert states == [DecisionState.MISSING_TIMEPOINT]
    assert DecisionState.ROUTINE_CONTINUE not in states


def test_monitoring_gap_signal_trips_on_wide_gap() -> None:
    assert compute_monitoring_gap([_draw(3), _draw(5), _draw(8)]).tripped is True
    assert compute_monitoring_gap(_DENSE).tripped is False


def test_escalation_levels() -> None:
    assert escalation_for([DecisionState.OHSS_RISK_ESCALATE]) == EscalationLevel.URGENT
    assert escalation_for([DecisionState.POOR_RESPONSE_FLAG]) == EscalationLevel.INFO
    assert escalation_for([DecisionState.MISSING_TIMEPOINT]) == EscalationLevel.INFO
    assert escalation_for([DecisionState.ROUTINE_CONTINUE]) == EscalationLevel.NONE
    assert escalation_for([DecisionState.AMBIGUOUS_REQUIRES_REVIEW]) == EscalationLevel.URGENT
