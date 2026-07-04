"""Shared fixtures/builders for the calculator unit tests.

The ``thresholds`` fixture is the reference ``thresholds.json`` payload — Lane D
must make ``data/synthetic/thresholds.json`` match this shape (see
``cyclesentinel.calculators.Thresholds``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cyclesentinel.calculators import Thresholds
from cyclesentinel.schemas import HormoneResult

_BASE = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)


def make_result(
    cycle_day: int,
    e2: float | None = None,
    *,
    progesterone: float | None = None,
    lh: float | None = None,
    mature_follicle_count: int | None = None,
    patient_id: str = "pat_1",
) -> HormoneResult:
    """Build a synthetic HormoneResult on ``cycle_day`` (drawn_at derived)."""
    return HormoneResult(
        id=f"res_d{cycle_day}",
        patient_id=patient_id,
        cycle_day=cycle_day,
        drawn_at=_BASE + timedelta(days=cycle_day),
        e2=e2,
        lh=lh,
        progesterone=progesterone,
        mature_follicle_count=mature_follicle_count,
    )


@pytest.fixture
def thresholds() -> Thresholds:
    """Reference threshold payload matching ``Thresholds`` / thresholds.json."""
    return {
        "ohss": {
            "e2_high": 3500.0,
            "rate_pct_per_day_high": 50.0,
            "mature_follicle_count_high": 18,
            "pcos_threshold_multiplier": 0.85,
        },
        "luteinization": {
            "progesterone_by_cycle_day": [
                {"max_cycle_day": 8, "threshold": 1.5},
                {"max_cycle_day": 12, "threshold": 1.75},
            ],
            "default_threshold": 2.0,
        },
        "poor_responder": {
            "flat_rate_pct_per_day": 20.0,
            "min_e2_on_trajectory": 500.0,
        },
    }
