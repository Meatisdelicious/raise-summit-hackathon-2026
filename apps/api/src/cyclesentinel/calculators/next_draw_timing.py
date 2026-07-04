"""Next monitoring interval from trajectory volatility (accelerating → shorter
interval). Emits ``value`` ``"24h"`` or ``"48h"``."""

from __future__ import annotations

from collections.abc import Sequence

from cyclesentinel.calculators._util import latest_e2_rate
from cyclesentinel.schemas import ComputedSignal, HormoneResult

# Monitoring cadence heuristic (not a clinical threshold): a latest E2 rise at
# or above this %/day is "accelerating" → tighten the next draw to 24h.
_ACCELERATING_PCT_PER_DAY = 40.0


def compute_next_draw_timing(trajectory: Sequence[HormoneResult]) -> ComputedSignal:
    """Recommended interval to the next monitoring draw.

    ``value`` is ``"24h"`` when the most recent E2 rate-of-rise is accelerating,
    else ``"48h"``. ``tripped`` marks the tighter (24h) cadence.
    """
    info = latest_e2_rate(trajectory)
    if info is not None and info.pct_per_day >= _ACCELERATING_PCT_PER_DAY:
        return ComputedSignal(
            name="next_draw_timing",
            value="24h",
            detail=(f"accelerating trajectory ({info.pct_per_day:+.0f}%/day) → next draw in 24h"),
            tripped=True,
        )
    slope = f"{info.pct_per_day:+.0f}%/day" if info is not None else "stable/sparse"
    return ComputedSignal(
        name="next_draw_timing",
        value="48h",
        detail=f"{slope} → next draw in 48h",
        tripped=False,
    )
