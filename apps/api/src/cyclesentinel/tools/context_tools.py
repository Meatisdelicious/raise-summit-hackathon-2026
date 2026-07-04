"""Context tools: ``get_patient_context`` and ``get_trajectory`` (read-only db reads).

These are the agent's first two steps — pull the patient's baseline markers and her serial
trajectory so the compute phase has something to reason over. Both read through
:mod:`cyclesentinel.db.repo`; neither retrieves a protocol rule (that is conditional, later).
"""

from __future__ import annotations

from pydantic import BaseModel

from cyclesentinel.db import repo
from cyclesentinel.schemas import HormoneResult, Patient
from cyclesentinel.tools.base import ToolContext, ToolError, make_tool, register


class GetPatientContextArgs(BaseModel):
    """Arguments for ``get_patient_context``."""

    patient_id: str


class GetTrajectoryArgs(BaseModel):
    """Arguments for ``get_trajectory``."""

    patient_id: str


class TrajectoryResult(BaseModel):
    """The patient's serial results (oldest-first), plus a convenience count."""

    patient_id: str
    results: list[HormoneResult]
    count: int


async def _get_patient_context(ctx: ToolContext, args: GetPatientContextArgs) -> Patient:
    patient = repo.get_patient(ctx.session, args.patient_id)
    if patient is None:
        raise ToolError(f"unknown patient: {args.patient_id!r}")
    return patient


async def _get_trajectory(ctx: ToolContext, args: GetTrajectoryArgs) -> TrajectoryResult:
    results = repo.list_results(ctx.session, args.patient_id)
    return TrajectoryResult(patient_id=args.patient_id, results=results, count=len(results))


get_patient_context = register(
    make_tool(
        name="get_patient_context",
        description=(
            "Return the patient's protocol type, current cycle day, and baseline markers "
            "(AMH, antral follicle count, PCOS flag)."
        ),
        args_model=GetPatientContextArgs,
        result_model=Patient,
        fn=_get_patient_context,
    )
)

get_trajectory = register(
    make_tool(
        name="get_trajectory",
        description=(
            "Return the patient's prior serial hormone results (time series), oldest-first."
        ),
        args_model=GetTrajectoryArgs,
        result_model=TrajectoryResult,
        fn=_get_trajectory,
    )
)
