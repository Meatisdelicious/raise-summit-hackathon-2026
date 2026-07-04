"""Compute tools are thin wrappers: each agrees byte-for-byte with its underlying calculator."""

from __future__ import annotations

from sqlalchemy.orm import Session

from cyclesentinel.calculators import (
    Thresholds,
    check_progesterone_for_day,
    compute_e2_per_follicle,
    compute_e2_rate,
    compute_next_draw_timing,
    compute_ohss_composite,
)
from cyclesentinel.db import repo
from cyclesentinel.schemas import ComputedSignal
from cyclesentinel.tools import get_tool
from cyclesentinel.tools.base import ToolContext


async def _run(ctx: ToolContext, name: str, args: dict[str, object]) -> ComputedSignal:
    result = await get_tool(name).invoke(ctx, args)
    assert isinstance(result, ComputedSignal)
    return result


async def test_compute_e2_rate_matches_calculator(ctx: ToolContext, session: Session) -> None:
    trajectory = repo.list_results(session, "pat_t")
    got = await _run(ctx, "compute_e2_rate", {"patient_id": "pat_t"})
    assert got == compute_e2_rate(trajectory)


async def test_compute_e2_per_follicle_matches_calculator(ctx: ToolContext) -> None:
    got = await _run(ctx, "compute_e2_per_follicle", {"result_id": "res_t2"})
    assert got == compute_e2_per_follicle(3200.0, 18)


async def test_compute_ohss_composite_matches_calculator(
    ctx: ToolContext, session: Session, thresholds: Thresholds
) -> None:
    trajectory = repo.list_results(session, "pat_t")
    rate = compute_e2_rate(trajectory).value
    assert isinstance(rate, float)
    expected = compute_ohss_composite(3200.0, rate, 18, True, thresholds)
    got = await _run(ctx, "compute_ohss_composite", {"patient_id": "pat_t", "result_id": "res_t2"})
    assert got == expected
    assert got.tripped is True  # converging OHSS picture on the seeded PCOS patient
    assert got.value == "high"


async def test_check_progesterone_for_day_matches_calculator(
    ctx: ToolContext, thresholds: Thresholds
) -> None:
    got = await _run(ctx, "check_progesterone_for_day", {"result_id": "res_t2"})
    assert got == check_progesterone_for_day(1.6, 8, thresholds)
    assert got.tripped is True  # 1.6 > day-8 threshold 1.5


async def test_compute_next_draw_timing_matches_calculator(
    ctx: ToolContext, session: Session
) -> None:
    trajectory = repo.list_results(session, "pat_t")
    got = await _run(ctx, "compute_next_draw_timing", {"patient_id": "pat_t"})
    assert got == compute_next_draw_timing(trajectory)
    assert got.value == "24h"  # accelerating trajectory tightens the cadence
