"""Context tools read patient + trajectory from the db and raise ToolError on unknown ids."""

from __future__ import annotations

import pytest

from cyclesentinel.schemas import Patient
from cyclesentinel.tools import ToolError, get_tool
from cyclesentinel.tools.base import ToolContext
from cyclesentinel.tools.context_tools import TrajectoryResult


async def test_get_patient_context_returns_baseline_markers(ctx: ToolContext) -> None:
    result = await get_tool("get_patient_context").invoke(ctx, {"patient_id": "pat_t"})
    assert isinstance(result, Patient)
    assert result.id == "pat_t"
    assert result.pcos_flag is True
    assert result.antral_follicle_count == 24


async def test_get_patient_context_unknown_raises_tool_error(ctx: ToolContext) -> None:
    with pytest.raises(ToolError):
        await get_tool("get_patient_context").invoke(ctx, {"patient_id": "nope"})


async def test_get_trajectory_is_oldest_first(ctx: ToolContext) -> None:
    result = await get_tool("get_trajectory").invoke(ctx, {"patient_id": "pat_t"})
    assert isinstance(result, TrajectoryResult)
    assert result.count == 2
    assert [r.cycle_day for r in result.results] == [6, 8]


async def test_get_trajectory_unknown_patient_is_empty(ctx: ToolContext) -> None:
    result = await get_tool("get_trajectory").invoke(ctx, {"patient_id": "nope"})
    assert isinstance(result, TrajectoryResult)
    assert result.count == 0
