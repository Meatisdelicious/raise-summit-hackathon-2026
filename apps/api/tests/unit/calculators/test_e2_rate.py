"""Tests for compute_e2_rate."""

from __future__ import annotations

from cyclesentinel.calculators import compute_e2_rate
from tests.unit.calculators.conftest import make_result


def test_steep_rise_reports_high_pct_per_day() -> None:
    # 1200 -> 3000 over 2 cycle days = +75%/day (killer-case precursor).
    results = [make_result(6, 1200.0), make_result(8, 3000.0)]
    sig = compute_e2_rate(results)
    assert sig.name == "e2_rate"
    assert isinstance(sig.value, float)
    assert sig.value == 75.0
    assert sig.tripped is False  # rate itself never trips


def test_uses_only_the_last_two_valid_draws() -> None:
    results = [make_result(4, 400.0), make_result(6, 1200.0), make_result(8, 3000.0)]
    sig = compute_e2_rate(results)
    assert sig.value == 75.0


def test_skips_draws_without_e2() -> None:
    results = [
        make_result(6, 1000.0),
        make_result(7, None, progesterone=1.0),
        make_result(8, 1500.0),
    ]
    # 1000 -> 1500 over 2 days = +25%/day
    sig = compute_e2_rate(results)
    assert sig.value == 25.0


def test_insufficient_data_does_not_trip() -> None:
    sig = compute_e2_rate([make_result(8, 1500.0)])
    assert sig.value == 0.0
    assert sig.tripped is False
    assert "insufficient" in sig.detail
