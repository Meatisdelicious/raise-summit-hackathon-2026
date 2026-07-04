"""Tests for check_progesterone_for_day (day-dependent threshold)."""

from __future__ import annotations

from cyclesentinel.calculators import Thresholds, check_progesterone_for_day


def test_borderline_p4_trips_on_day_8(thresholds: Thresholds) -> None:
    # Day-8 threshold is 1.5; 1.6 crosses (killer-case luteinization flag).
    sig = check_progesterone_for_day(1.6, 8, thresholds)
    assert sig.name == "progesterone_for_day"
    assert sig.value == 1.6
    assert sig.tripped is True


def test_normal_p4_does_not_trip(thresholds: Thresholds) -> None:
    sig = check_progesterone_for_day(0.8, 8, thresholds)
    assert sig.tripped is False


def test_threshold_is_day_dependent(thresholds: Thresholds) -> None:
    # 1.6 trips on day 8 (limit 1.5) but not on day 11 (limit 1.75).
    assert check_progesterone_for_day(1.6, 8, thresholds).tripped is True
    assert check_progesterone_for_day(1.6, 11, thresholds).tripped is False


def test_falls_back_to_default_threshold(thresholds: Thresholds) -> None:
    # cycle_day beyond all bands -> default_threshold 2.0.
    assert check_progesterone_for_day(1.9, 20, thresholds).tripped is False
    assert check_progesterone_for_day(2.1, 20, thresholds).tripped is True


def test_missing_progesterone_does_not_trip(thresholds: Thresholds) -> None:
    sig = check_progesterone_for_day(None, 8, thresholds)
    assert sig.value == 0.0
    assert sig.tripped is False
