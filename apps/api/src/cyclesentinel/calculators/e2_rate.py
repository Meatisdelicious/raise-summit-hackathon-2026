"""E2 rate-of-rise between the two most recent serial draws (Δ and %/day)."""

from __future__ import annotations

from collections.abc import Sequence

from cyclesentinel.calculators._util import latest_e2_rate
from cyclesentinel.schemas import ComputedSignal, HormoneResult


def compute_e2_rate(results: Sequence[HormoneResult]) -> ComputedSignal:
    """Estradiol rate-of-rise between the last two valid draws.

    ``value`` is the rise in %/day (feeds :func:`compute_ohss_composite`). This
    signal never trips on its own — the OHSS composite owns that decision.
    """
    info = latest_e2_rate(results)
    if info is None:
        return ComputedSignal(
            name="e2_rate",
            value=0.0,
            detail="insufficient serial E2 data (need two valid draws)",
            tripped=False,
        )
    return ComputedSignal(
        name="e2_rate",
        value=round(info.pct_per_day, 1),
        detail=(f"E2 {info.delta:+.0f} pg/mL over {info.days:.1f}d ({info.pct_per_day:+.0f}%/day)"),
        tripped=False,
    )
