"""Tests for compute_next_draw_timing (accelerating -> 24h)."""

from __future__ import annotations

from cyclesentinel.calculators import compute_next_draw_timing
from tests.unit.calculators.conftest import make_result


def test_accelerating_trajectory_yields_24h() -> None:
    # 1200 -> 3000 over 2 days = +75%/day (>= 40) -> tighten to 24h.
    traj = [make_result(6, 1200.0), make_result(8, 3000.0)]
    sig = compute_next_draw_timing(traj)
    assert sig.value == "24h"
    assert sig.tripped is True


def test_stable_trajectory_yields_48h() -> None:
    # 1000 -> 1150 over 2 days = +7.5%/day (< 40) -> 48h.
    traj = [make_result(6, 1000.0), make_result(8, 1150.0)]
    sig = compute_next_draw_timing(traj)
    assert sig.value == "48h"
    assert sig.tripped is False


def test_sparse_trajectory_defaults_to_48h() -> None:
    sig = compute_next_draw_timing([make_result(8, 1500.0)])
    assert sig.value == "48h"
    assert sig.tripped is False
