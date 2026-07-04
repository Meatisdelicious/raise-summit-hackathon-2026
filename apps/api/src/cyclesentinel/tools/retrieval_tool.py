"""The conditional retrieval tool: ``retrieve_protocol_rule``.

This is the "not RAG" core — it is called **only** when a computed signal trips a branch, never
unconditionally. It runs the visual document retriever (Vultron Prime-8B) for one ``rule_type``,
returns the scored page hits, and selects the best :class:`Citation` (with a quote drawn from the
top page's text layer, so it resolves to a real page per hard rule 3).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from cyclesentinel.enums import RuleType
from cyclesentinel.schemas import Citation, RetrievalHit
from cyclesentinel.tools.base import ToolContext, ToolError, make_tool, register


class RetrieveProtocolRuleArgs(BaseModel):
    """Arguments for ``retrieve_protocol_rule``."""

    query: str
    rule_type: RuleType
    top_k: int = Field(default=3, ge=1, le=10)


class RuleRetrievalResult(BaseModel):
    """The retrieved pages for one rule plus the selected citation (``retrieve_rule`` shape)."""

    rule_type: RuleType
    hits: list[RetrievalHit]
    citation: Citation


def _quote_from(text: str) -> str:
    """Pick a representative quote: the first non-empty line of the page's text layer."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return text.strip()


async def _retrieve_protocol_rule(
    ctx: ToolContext, args: RetrieveProtocolRuleArgs
) -> RuleRetrievalResult:
    hits = await ctx.retriever.retrieve(args.query, args.rule_type, args.top_k)
    # Defensive filter: the store already filters by rule_type; never let a mismatched page cite.
    hits = [h for h in hits if str(h.rule_type) == str(args.rule_type)]
    if not hits:
        raise ToolError(f"no protocol pages retrieved for rule_type={args.rule_type!r}")

    top = hits[0]
    citation = Citation(
        doc_id=top.doc_id,
        rule_type=top.rule_type,
        page=top.page,
        article=top.article,
        quote=_quote_from(top.text),
        score=top.score,
    )
    return RuleRetrievalResult(rule_type=args.rule_type, hits=hits, citation=citation)


retrieve_protocol_rule = register(
    make_tool(
        name="retrieve_protocol_rule",
        description=(
            "Conditionally retrieve the governing protocol/SOP page(s) for a rule_type "
            "(ohss | luteinization | poor_responder | stimulation) via visual document retrieval, "
            "returning scored pages plus the selected citation. Call this only when a computed "
            "signal calls for a specific rule."
        ),
        args_model=RetrieveProtocolRuleArgs,
        result_model=RuleRetrievalResult,
        fn=_retrieve_protocol_rule,
    )
)
