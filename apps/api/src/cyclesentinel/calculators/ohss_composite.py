"""OHSS-risk composite — combine E2 level, rate-of-rise, mature follicle count
and PCOS status into a risk tier. Trips ``OHSS_RISK_ESCALATE``."""

from __future__ import annotations

from cyclesentinel.calculators._util import Thresholds
from cyclesentinel.schemas import ComputedSignal


def compute_ohss_composite(
    e2: float | None,
    rate_pct_per_day: float,
    mature_follicle_count: int | None,
    pcos_flag: bool,
    thresholds: Thresholds,
) -> ComputedSignal:
    """Composite OHSS risk tier.

    Counts how many of three criteria cross their (PCOS-adjusted) thresholds:
    absolute E2, E2 rate-of-rise, mature follicle count. ``value`` is the tier
    (``"low"`` / ``"moderate"`` / ``"high"``); it **trips** when >= 2 criteria
    cross — the fail-safe pattern so a single borderline number can't escalate,
    but a converging picture does.
    """
    t = thresholds["ohss"]
    mult = t["pcos_threshold_multiplier"] if pcos_flag else 1.0
    e2_lim = t["e2_high"] * mult
    rate_lim = t["rate_pct_per_day_high"] * mult
    foll_lim = t["mature_follicle_count_high"] * mult

    crossed: list[str] = []
    if e2 is not None and e2 >= e2_lim:
        crossed.append(f"E2 {e2:.0f}>={e2_lim:.0f}")
    if rate_pct_per_day >= rate_lim:
        crossed.append(f"rate {rate_pct_per_day:.0f}>={rate_lim:.0f}%/day")
    if mature_follicle_count is not None and mature_follicle_count >= foll_lim:
        crossed.append(f"follicles {mature_follicle_count}>={foll_lim:.0f}")

    n = len(crossed)
    tier = "high" if n >= 2 else "moderate" if n == 1 else "low"
    pcos_note = " (PCOS-lowered thresholds)" if pcos_flag else ""
    detail = (
        f"OHSS risk {tier}: {', '.join(crossed)}{pcos_note}"
        if crossed
        else f"OHSS risk low: no criteria crossed{pcos_note}"
    )
    return ComputedSignal(
        name="ohss_composite",
        value=tier,
        detail=detail,
        tripped=n >= 2,
    )
