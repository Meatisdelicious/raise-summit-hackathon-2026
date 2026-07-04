"""The dose-adjustment tool: ``lookup_dose_adjustment`` (reads ``dose_tables.json`` via ``ctx``).

Given a computed ``situation`` (routine / poor_response / ohss_risk / premature_luteinization), it
returns the advisory gonadotropin dose-adjustment range plus the protocol citation. The delta is a
*range a human validates* — never an autonomous prescription (``docs/safety.md``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cyclesentinel.enums import RuleType
from cyclesentinel.schemas import Citation
from cyclesentinel.tools.base import DoseRule, ToolContext, ToolError, make_tool, register

Situation = Literal["routine", "poor_response", "ohss_risk", "premature_luteinization"]


class LookupDoseAdjustmentArgs(BaseModel):
    """Arguments for ``lookup_dose_adjustment``."""

    situation: Situation


class DoseAdjustmentResult(BaseModel):
    """The advisory dose adjustment for a situation, grounded in a protocol citation."""

    situation: str
    action: str
    delta_iu_range: tuple[int, int] | None
    citation: Citation
    detail: str


def load_dose_rules(path: str | Path) -> dict[str, DoseRule]:
    """Parse ``dose_tables.json`` into a ``{situation: DoseRule}`` map for the tool context."""
    raw: object = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"malformed dose table (expected object): {path}")
    rows = raw.get("gonadotropin_adjustments")
    if not isinstance(rows, list):
        raise ValueError(f"dose table missing 'gonadotropin_adjustments' array: {path}")

    table: dict[str, DoseRule] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        citation = row["citation"]
        delta = row["delta_iu_range"]
        delta_range = (int(delta[0]), int(delta[1])) if isinstance(delta, list) else None
        table[str(row["situation"])] = DoseRule(
            situation=str(row["situation"]),
            action=str(row["action"]),
            delta_iu_range=delta_range,
            doc_id=str(citation["doc_id"]),
            rule_type=RuleType(str(citation["rule_type"])),
            page=int(citation["page"]),
            article=str(citation["article"]),
        )
    return table


def _dose_quote(ctx: ToolContext, rule: DoseRule) -> str:
    """A citation quote for the dose rule: the cited page's first line if the corpus is loaded."""
    if ctx.corpus is not None:
        try:
            text = ctx.corpus.get_page_text(rule.doc_id, rule.page)
        except KeyError:
            text = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
    if rule.delta_iu_range is not None:
        low, high = rule.delta_iu_range
        return f"{rule.action}: {low:+d} to {high:+d} IU"
    return rule.action


async def _lookup_dose_adjustment(
    ctx: ToolContext, args: LookupDoseAdjustmentArgs
) -> DoseAdjustmentResult:
    rule = ctx.dose_table.get(args.situation)
    if rule is None:
        raise ToolError(f"no dose rule for situation={args.situation!r}")
    if rule.delta_iu_range is None:
        detail = f"{args.situation}: {rule.action} (no numeric IU delta)"
    else:
        low, high = rule.delta_iu_range
        detail = f"{args.situation}: {rule.action} ({low:+d} to {high:+d} IU)"
    citation = Citation(
        doc_id=rule.doc_id,
        rule_type=rule.rule_type,
        page=rule.page,
        article=rule.article,
        quote=_dose_quote(ctx, rule),
    )
    return DoseAdjustmentResult(
        situation=args.situation,
        action=rule.action,
        delta_iu_range=rule.delta_iu_range,
        citation=citation,
        detail=detail,
    )


lookup_dose_adjustment = register(
    make_tool(
        name="lookup_dose_adjustment",
        description=(
            "Look up the advisory gonadotropin dose-adjustment range (IU) and citation for a "
            "computed situation: routine | poor_response | ohss_risk | premature_luteinization."
        ),
        args_model=LookupDoseAdjustmentArgs,
        result_model=DoseAdjustmentResult,
        fn=_lookup_dose_adjustment,
    )
)
