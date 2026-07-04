"""retrieve_protocol_rule returns hits + citation for the requested rule_type (stub mode)."""

from __future__ import annotations

import pytest

from cyclesentinel.enums import RuleType
from cyclesentinel.schemas import RetrievalHit
from cyclesentinel.tools import ToolError, get_tool
from cyclesentinel.tools.base import ToolContext
from cyclesentinel.tools.retrieval_tool import RuleRetrievalResult


async def test_retrieve_returns_hits_and_citation_for_rule_type(ctx: ToolContext) -> None:
    result = await get_tool("retrieve_protocol_rule").invoke(
        ctx, {"query": "steep E2 rise OHSS", "rule_type": "ohss", "top_k": 3}
    )
    assert isinstance(result, RuleRetrievalResult)
    assert str(result.rule_type) == "ohss"
    assert result.hits and all(str(h.rule_type) == "ohss" for h in result.hits)
    # citation is drawn from the top hit and stays tagged with the requested rule_type
    assert str(result.citation.rule_type) == "ohss"
    assert result.citation.doc_id == result.hits[0].doc_id
    assert result.citation.page == result.hits[0].page
    assert result.citation.score == result.hits[0].score
    assert result.citation.quote  # a non-empty quote from the page text layer


class _MismatchedRetriever:
    """A retriever that returns a page tagged with the *wrong* rule_type (must be filtered out)."""

    async def retrieve(self, query: str, rule_type: RuleType, top_k: int) -> list[RetrievalHit]:
        wrong = "stimulation" if str(rule_type) != "stimulation" else "ohss"
        return [
            RetrievalHit(
                doc_id="x",
                rule_type=RuleType(wrong),
                page=1,
                score=0.5,
                text="mismatched page",
                article="§9",
            )
        ]


async def test_retrieve_filters_out_mismatched_rule_type(ctx: ToolContext) -> None:
    ctx.retriever = _MismatchedRetriever()
    with pytest.raises(ToolError):
        await get_tool("retrieve_protocol_rule").invoke(ctx, {"query": "q", "rule_type": "ohss"})
