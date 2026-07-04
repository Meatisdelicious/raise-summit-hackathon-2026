"""lookup_dose_adjustment reads dose_tables.json and grounds each situation to a citation."""

from __future__ import annotations

import pytest

from cyclesentinel.tools import DoseRule, ToolError, get_tool
from cyclesentinel.tools.base import ToolContext
from cyclesentinel.tools.dose_tool import DoseAdjustmentResult


def test_load_dose_rules_parses_all_situations(dose_table: dict[str, DoseRule]) -> None:
    assert set(dose_table) == {
        "routine",
        "poor_response",
        "ohss_risk",
        "premature_luteinization",
    }


@pytest.mark.parametrize(
    ("situation", "action", "delta", "doc_id", "article"),
    [
        ("routine", "maintain", (0, 0), "stimulation", "§1.3"),
        ("poor_response", "increase", (75, 150), "poor_responder", "§3.2"),
        ("ohss_risk", "reduce_or_coast", (-150, -75), "ohss_sop", "§4.2"),
        ("premature_luteinization", "freeze_all_consider", None, "luteinization", "§2.4"),
    ],
)
async def test_lookup_dose_adjustment(
    ctx: ToolContext,
    situation: str,
    action: str,
    delta: tuple[int, int] | None,
    doc_id: str,
    article: str,
) -> None:
    result = await get_tool("lookup_dose_adjustment").invoke(ctx, {"situation": situation})
    assert isinstance(result, DoseAdjustmentResult)
    assert result.situation == situation
    assert result.action == action
    assert result.delta_iu_range == delta
    assert result.citation.doc_id == doc_id
    assert result.citation.article == article
    assert result.citation.quote  # a non-empty grounding quote


async def test_lookup_dose_adjustment_missing_rule_raises(ctx: ToolContext) -> None:
    ctx.dose_table = {}
    with pytest.raises(ToolError):
        await get_tool("lookup_dose_adjustment").invoke(ctx, {"situation": "routine"})
