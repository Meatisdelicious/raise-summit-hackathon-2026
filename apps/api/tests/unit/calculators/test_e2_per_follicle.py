"""Tests for compute_e2_per_follicle."""

from __future__ import annotations

from cyclesentinel.calculators import compute_e2_per_follicle


def test_ratio_is_e2_over_follicles() -> None:
    sig = compute_e2_per_follicle(3000.0, 12)
    assert sig.name == "e2_per_follicle"
    assert sig.value == 250.0
    assert sig.tripped is False


def test_zero_follicles_returns_zero() -> None:
    sig = compute_e2_per_follicle(3000.0, 0)
    assert sig.value == 0.0
    assert sig.tripped is False


def test_missing_inputs_return_zero() -> None:
    assert compute_e2_per_follicle(None, 10).value == 0.0
    assert compute_e2_per_follicle(3000.0, None).value == 0.0
