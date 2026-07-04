"""``branches_for`` — pure mapping from tripped signals to the rule(s) to retrieve."""

from __future__ import annotations

from cyclesentinel.agent import branches_for
from cyclesentinel.enums import RuleType
from cyclesentinel.schemas import ComputedSignal


def _sig(name: str, *, tripped: bool) -> ComputedSignal:
    return ComputedSignal(name=name, value=0.0, detail="", tripped=tripped)


def test_no_trips_yields_no_branches() -> None:
    signals = [
        _sig("ohss_composite", tripped=False),
        _sig("progesterone_for_day", tripped=False),
        _sig("response_curve", tripped=False),
    ]
    assert branches_for(signals) == []


def test_ohss_and_luteinization_in_order() -> None:
    signals = [
        _sig("ohss_composite", tripped=True),
        _sig("progesterone_for_day", tripped=True),
        _sig("response_curve", tripped=False),
    ]
    assert branches_for(signals) == [RuleType.OHSS, RuleType.LUTEINIZATION]


def test_poor_responder_only() -> None:
    signals = [
        _sig("ohss_composite", tripped=False),
        _sig("response_curve", tripped=True),
    ]
    assert branches_for(signals) == [RuleType.POOR_RESPONDER]


def test_each_rule_appears_at_most_once() -> None:
    signals = [_sig("ohss_composite", tripped=True), _sig("ohss_composite", tripped=True)]
    assert branches_for(signals) == [RuleType.OHSS]
