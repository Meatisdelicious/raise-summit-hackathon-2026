"""Brief tools assemble a cited, unvalidated MonitoringBrief and record escalations."""

from __future__ import annotations

from cyclesentinel.schemas import Citation, MonitoringBrief
from cyclesentinel.tools import get_tool
from cyclesentinel.tools.base import ToolContext
from cyclesentinel.tools.brief_tools import EscalationResult


async def test_create_monitoring_brief_assembles_unvalidated_brief(ctx: ToolContext) -> None:
    citation = Citation(
        doc_id="ohss_sop", rule_type="ohss", page=4, article="§4.2", quote="coasting"
    )
    result = await get_tool("create_monitoring_brief").invoke(
        ctx,
        {
            "patient_id": "pat_t",
            "result_id": "res_t2",
            "run_id": "run-xyz",
            "states": ["OHSS_RISK_ESCALATE", "PREMATURE_LUTEINIZATION_FLAG"],
            "interpretation": "steep E2 rise with borderline P4",
            "recommended_action": "coast; next draw 24h",
            "citations": [citation.model_dump()],
            "escalation_level": "urgent",
        },
    )
    assert isinstance(result, MonitoringBrief)
    assert result.id == "brief-0001"  # deterministic IdFactory
    assert result.states == ["OHSS_RISK_ESCALATE", "PREMATURE_LUTEINIZATION_FLAG"]
    assert result.escalation_level == "urgent"
    assert result.citations[0].doc_id == "ohss_sop"
    # a human must still validate before it reaches the clinic
    assert result.validated_by is None
    assert result.validated_at is None
    assert result.created_at is not None


async def test_create_monitoring_brief_defaults_are_safe(ctx: ToolContext) -> None:
    result = await get_tool("create_monitoring_brief").invoke(
        ctx,
        {
            "patient_id": "pat_t",
            "result_id": "res_t2",
            "run_id": "run-xyz",
            "states": ["ROUTINE_CONTINUE"],
            "interpretation": "within expected bounds",
            "recommended_action": "continue; next draw 48h",
        },
    )
    assert isinstance(result, MonitoringBrief)
    assert result.citations == []
    assert result.escalation_level == "none"


async def test_escalate_to_biologist_requires_human_validation(ctx: ToolContext) -> None:
    result = await get_tool("escalate_to_biologist").invoke(
        ctx, {"level": "urgent", "reason": "OHSS composite high"}
    )
    assert isinstance(result, EscalationResult)
    assert result.level == "urgent"
    assert result.to == "biologist"
    assert result.requires_human_validation is True
    assert "OHSS composite high" in result.detail
