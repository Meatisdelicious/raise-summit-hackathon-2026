"""Progesterone vs the cycle-day-dependent threshold. Trips
``PREMATURE_LUTEINIZATION_FLAG``."""

from __future__ import annotations

from cyclesentinel.calculators._util import Thresholds
from cyclesentinel.schemas import ComputedSignal


def check_progesterone_for_day(
    progesterone: float | None,
    cycle_day: int,
    thresholds: Thresholds,
) -> ComputedSignal:
    """Compare progesterone (ng/mL) against the threshold for this cycle day.

    The threshold is day-dependent: the first band whose ``max_cycle_day`` is
    at least ``cycle_day`` wins, else ``default_threshold``. ``value`` is the
    progesterone level; it **trips** when the level exceeds the threshold.
    """
    t = thresholds["luteinization"]
    if progesterone is None:
        return ComputedSignal(
            name="progesterone_for_day",
            value=0.0,
            detail="no progesterone value on this draw",
            tripped=False,
        )

    threshold = t["default_threshold"]
    for band in sorted(t["progesterone_by_cycle_day"], key=lambda b: b["max_cycle_day"]):
        if cycle_day <= band["max_cycle_day"]:
            threshold = band["threshold"]
            break

    tripped = progesterone > threshold
    relation = ">" if tripped else "<="
    return ComputedSignal(
        name="progesterone_for_day",
        value=round(progesterone, 2),
        detail=(
            f"P4 {progesterone:.2f} ng/mL {relation} day-{cycle_day} threshold {threshold:.2f}"
        ),
        tripped=tripped,
    )
