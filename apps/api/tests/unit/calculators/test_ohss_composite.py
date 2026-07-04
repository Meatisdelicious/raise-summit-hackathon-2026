"""Tests for compute_ohss_composite (K-case trips, R-case does not)."""

from __future__ import annotations

from cyclesentinel.calculators import Thresholds, compute_ohss_composite


def test_killer_case_trips_high(thresholds: Thresholds) -> None:
    # High E2 + steep rate + many follicles + PCOS -> all three cross -> high.
    sig = compute_ohss_composite(
        e2=4200.0,
        rate_pct_per_day=75.0,
        mature_follicle_count=22,
        pcos_flag=True,
        thresholds=thresholds,
    )
    assert sig.value == "high"
    assert sig.tripped is True


def test_routine_case_does_not_trip(thresholds: Thresholds) -> None:
    sig = compute_ohss_composite(
        e2=1200.0,
        rate_pct_per_day=30.0,
        mature_follicle_count=9,
        pcos_flag=False,
        thresholds=thresholds,
    )
    assert sig.value == "low"
    assert sig.tripped is False


def test_single_criterion_is_moderate_not_tripped(thresholds: Thresholds) -> None:
    # Only rate crosses (50%/day limit); E2 and follicles below.
    sig = compute_ohss_composite(
        e2=1500.0,
        rate_pct_per_day=60.0,
        mature_follicle_count=10,
        pcos_flag=False,
        thresholds=thresholds,
    )
    assert sig.value == "moderate"
    assert sig.tripped is False


def test_pcos_lowers_thresholds_enough_to_trip(thresholds: Thresholds) -> None:
    # E2 3100 and rate 45 are BELOW the base limits (3500 / 50) but PCOS
    # multiplier 0.85 lowers them to 2975 / 42.5 -> both cross -> trips.
    base = compute_ohss_composite(3100.0, 45.0, 5, pcos_flag=False, thresholds=thresholds)
    pcos = compute_ohss_composite(3100.0, 45.0, 5, pcos_flag=True, thresholds=thresholds)
    assert base.tripped is False
    assert pcos.tripped is True
    assert pcos.value == "high"


def test_none_e2_is_handled(thresholds: Thresholds) -> None:
    sig = compute_ohss_composite(None, 60.0, 25, pcos_flag=False, thresholds=thresholds)
    # rate + follicles cross -> still trips without an E2 value.
    assert sig.tripped is True
