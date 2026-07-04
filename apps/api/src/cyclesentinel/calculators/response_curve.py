"""Response-curve check — compare the trajectory to the expected stimulation
curve. This is the 6th calculator; it runs in the compute phase as a
ComputedSignal (NOT a tool) and, when tripped, drives ``POOR_RESPONSE_FLAG``."""

from __future__ import annotations

from collections.abc import Sequence

from cyclesentinel.calculators._util import Thresholds, days_between, sorted_e2_points
from cyclesentinel.enums import Protocol
from cyclesentinel.schemas import ComputedSignal, HormoneResult


def compute_response_curve(
    trajectory: Sequence[HormoneResult],
    protocol: Protocol,
    thresholds: Thresholds,
) -> ComputedSignal:
    """Average E2 slope across the whole trajectory vs the expected curve.

    ``value`` is the average rise in %/day (first valid draw → last). It
    **trips** (poor responder) only when the trajectory is *both* flat (slope
    below ``flat_rate_pct_per_day``) *and* still low overall (latest E2 below
    ``min_e2_on_trajectory``) — requiring both avoids flagging an early cycle
    that simply hasn't climbed yet.
    """
    t = thresholds["poor_responder"]
    pts = sorted_e2_points(trajectory)
    if len(pts) < 2:
        return ComputedSignal(
            name="response_curve",
            value=0.0,
            detail="insufficient trajectory to assess response",
            tripped=False,
        )

    first, last = pts[0], pts[-1]
    first_e2, last_e2 = first.e2, last.e2
    if first_e2 is None or last_e2 is None or first_e2 <= 0:
        return ComputedSignal(
            name="response_curve",
            value=0.0,
            detail="insufficient trajectory to assess response",
            tripped=False,
        )

    days = days_between(first, last)
    if days <= 0:
        return ComputedSignal(
            name="response_curve",
            value=0.0,
            detail="trajectory spans no time to assess response",
            tripped=False,
        )

    avg_pct_per_day = ((last_e2 - first_e2) / first_e2 / days) * 100.0
    flat = avg_pct_per_day < t["flat_rate_pct_per_day"]
    low = last_e2 < t["min_e2_on_trajectory"]
    tripped = flat and low

    verdict = "flat + low (poor response)" if tripped else "within expected range"
    return ComputedSignal(
        name="response_curve",
        value=round(avg_pct_per_day, 1),
        detail=(
            f"{str(protocol)}: E2 avg {avg_pct_per_day:+.0f}%/day, "
            f"latest {last_e2:.0f} pg/mL — {verdict}"
        ),
        tripped=tripped,
    )
