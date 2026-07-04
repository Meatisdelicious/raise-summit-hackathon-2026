"""Tests for compute_response_curve (P-case flat trips poor_responder)."""

from __future__ import annotations

from cyclesentinel.calculators import Thresholds, compute_response_curve
from cyclesentinel.enums import Protocol
from tests.unit.calculators.conftest import make_result


def test_flat_and_low_trips_poor_responder(thresholds: Thresholds) -> None:
    # 200 -> 260 over 6 days = ~5%/day (flat, < 20) and latest 260 < 500 (low).
    traj = [make_result(3, 200.0), make_result(6, 230.0), make_result(9, 260.0)]
    sig = compute_response_curve(traj, Protocol.ANTAGONIST, thresholds)
    assert sig.name == "response_curve"
    assert sig.tripped is True


def test_healthy_rise_does_not_trip(thresholds: Thresholds) -> None:
    # 300 -> 3000 over 6 days climbs fast -> not flat.
    traj = [make_result(3, 300.0), make_result(6, 1200.0), make_result(9, 3000.0)]
    sig = compute_response_curve(traj, Protocol.ANTAGONIST, thresholds)
    assert sig.tripped is False
    assert isinstance(sig.value, float)
    assert sig.value > 20.0


def test_flat_but_high_does_not_trip(thresholds: Thresholds) -> None:
    # Slow slope but already at a healthy absolute level (>= 500) -> not poor.
    traj = [make_result(6, 2000.0), make_result(9, 2200.0)]
    sig = compute_response_curve(traj, Protocol.LONG_AGONIST, thresholds)
    assert sig.tripped is False


def test_insufficient_trajectory_does_not_trip(thresholds: Thresholds) -> None:
    sig = compute_response_curve([make_result(6, 200.0)], Protocol.ANTAGONIST, thresholds)
    assert sig.value == 0.0
    assert sig.tripped is False
