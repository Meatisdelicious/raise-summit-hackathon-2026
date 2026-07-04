"""Estradiol per mature follicle — distinguishes "high E2 from many follicles"
from an outlier. Informational; feeds the OHSS composite, never trips alone."""

from __future__ import annotations

from cyclesentinel.schemas import ComputedSignal


def compute_e2_per_follicle(
    e2: float | None,
    mature_follicle_count: int | None,
) -> ComputedSignal:
    """E2 (pg/mL) divided by mature follicle count.

    ``value`` is the ratio (0.0 when it can't be computed). No threshold is
    passed, so this signal is purely descriptive (``tripped`` is always False).
    """
    if e2 is None or mature_follicle_count is None or mature_follicle_count <= 0:
        return ComputedSignal(
            name="e2_per_follicle",
            value=0.0,
            detail="no E2 / mature-follicle count available",
            tripped=False,
        )
    ratio = e2 / mature_follicle_count
    return ComputedSignal(
        name="e2_per_follicle",
        value=round(ratio, 1),
        detail=f"{ratio:.0f} pg/mL per mature follicle ({mature_follicle_count} follicles)",
        tripped=False,
    )
