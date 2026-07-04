"""Compute tools: thin wrappers over the deterministic calculators.

Each tool takes *identifiers* (patient / result id) rather than raw hormone values, reads the actual
synthetic data from the db, and calls the matching pure calculator with thresholds pulled from
``ctx.thresholds``. Taking ids (not numbers) keeps the LLM from ever supplying a clinical value,
so the deterministic calculators stay authoritative — the safety posture in ``docs/safety.md``.

Five of the six calculators are exposed here; the sixth (``response_curve``) runs in the agent's
compute phase as a ComputedSignal, not as a tool.
"""

from __future__ import annotations

from pydantic import BaseModel

from cyclesentinel.calculators import (
    check_progesterone_for_day,
    compute_e2_per_follicle,
    compute_e2_rate,
    compute_next_draw_timing,
    compute_ohss_composite,
)
from cyclesentinel.db import repo
from cyclesentinel.schemas import ComputedSignal, HormoneResult
from cyclesentinel.tools.base import ToolContext, ToolError, make_tool, register


class PatientTrajectoryArgs(BaseModel):
    """Arguments for a compute tool that reasons over the whole trajectory."""

    patient_id: str


class ResultArgs(BaseModel):
    """Arguments for a compute tool that reasons over a single draw."""

    result_id: str


class OhssCompositeArgs(BaseModel):
    """Arguments for ``compute_ohss_composite`` (the draw, the trajectory, and PCOS status)."""

    patient_id: str
    result_id: str


def _require_result(ctx: ToolContext, result_id: str) -> HormoneResult:
    result = repo.get_result(ctx.session, result_id)
    if result is None:
        raise ToolError(f"unknown result: {result_id!r}")
    return result


def _rate_pct_per_day(trajectory: list[HormoneResult]) -> float:
    """The E2 rate-of-rise (%/day) as the OHSS composite expects it (0.0 when unavailable)."""
    value = compute_e2_rate(trajectory).value
    return float(value) if isinstance(value, (int, float)) else 0.0


async def _compute_e2_rate(ctx: ToolContext, args: PatientTrajectoryArgs) -> ComputedSignal:
    return compute_e2_rate(repo.list_results(ctx.session, args.patient_id))


async def _compute_e2_per_follicle(ctx: ToolContext, args: ResultArgs) -> ComputedSignal:
    result = _require_result(ctx, args.result_id)
    return compute_e2_per_follicle(result.e2, result.mature_follicle_count)


async def _compute_ohss_composite(ctx: ToolContext, args: OhssCompositeArgs) -> ComputedSignal:
    patient = repo.get_patient(ctx.session, args.patient_id)
    if patient is None:
        raise ToolError(f"unknown patient: {args.patient_id!r}")
    result = _require_result(ctx, args.result_id)
    trajectory = repo.list_results(ctx.session, args.patient_id)
    return compute_ohss_composite(
        result.e2,
        _rate_pct_per_day(trajectory),
        result.mature_follicle_count,
        patient.pcos_flag,
        ctx.thresholds,
    )


async def _check_progesterone_for_day(ctx: ToolContext, args: ResultArgs) -> ComputedSignal:
    result = _require_result(ctx, args.result_id)
    return check_progesterone_for_day(result.progesterone, result.cycle_day, ctx.thresholds)


async def _compute_next_draw_timing(
    ctx: ToolContext, args: PatientTrajectoryArgs
) -> ComputedSignal:
    return compute_next_draw_timing(repo.list_results(ctx.session, args.patient_id))


tool_compute_e2_rate = register(
    make_tool(
        name="compute_e2_rate",
        description="Compute the E2 rate-of-rise (Δ and %/day) between the last two serial draws.",
        args_model=PatientTrajectoryArgs,
        result_model=ComputedSignal,
        fn=_compute_e2_rate,
    )
)

tool_compute_e2_per_follicle = register(
    make_tool(
        name="compute_e2_per_follicle",
        description="Compute estradiol per mature follicle for a single draw.",
        args_model=ResultArgs,
        result_model=ComputedSignal,
        fn=_compute_e2_per_follicle,
    )
)

tool_compute_ohss_composite = register(
    make_tool(
        name="compute_ohss_composite",
        description=(
            "Compute the OHSS-risk composite tier from E2 level, rate-of-rise, mature follicle "
            "count, and PCOS flag."
        ),
        args_model=OhssCompositeArgs,
        result_model=ComputedSignal,
        fn=_compute_ohss_composite,
    )
)

tool_check_progesterone_for_day = register(
    make_tool(
        name="check_progesterone_for_day",
        description="Compare a draw's progesterone against the cycle-day-dependent threshold.",
        args_model=ResultArgs,
        result_model=ComputedSignal,
        fn=_check_progesterone_for_day,
    )
)

tool_compute_next_draw_timing = register(
    make_tool(
        name="compute_next_draw_timing",
        description="Recommend the next monitoring interval (24h vs 48h) from the trajectory.",
        args_model=PatientTrajectoryArgs,
        result_model=ComputedSignal,
        fn=_compute_next_draw_timing,
    )
)
