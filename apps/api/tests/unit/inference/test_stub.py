"""Stub clients: scripted LLM responses pop in order; retriever returns canned rule-typed hits."""

from __future__ import annotations

from cyclesentinel.enums import RuleType
from cyclesentinel.inference.base import ChatMessage, ChatResponse, ToolCall
from cyclesentinel.inference.stub import StubLLMClient, StubRetriever


async def test_stub_llm_returns_scripted_then_default() -> None:
    scripted = ChatResponse(
        content=None,
        tool_calls=[ToolCall(id="c1", name="get_trajectory", arguments={})],
    )
    client = StubLLMClient(responses=[scripted])
    first = await client.chat([ChatMessage(role="user", content="plan")])
    assert first.tool_calls[0].name == "get_trajectory"
    # queue drained → canned default
    second = await client.chat([ChatMessage(role="user", content="again")])
    assert second.tool_calls == []
    assert second.content is not None
    assert client.calls == 2


async def test_stub_llm_pops_in_order() -> None:
    r1 = ChatResponse(content="one")
    r2 = ChatResponse(content="two")
    client = StubLLMClient(responses=[r1, r2])
    assert (await client.chat([])).content == "one"
    assert (await client.chat([])).content == "two"


async def test_stub_retriever_returns_canned_hit_for_rule_type() -> None:
    retriever = StubRetriever()
    hits = await retriever.retrieve("OHSS composite", RuleType.OHSS, 3)
    assert len(hits) == 1
    assert hits[0].rule_type == RuleType.OHSS
    assert hits[0].doc_id == "stub-ohss"
    assert "OHSS composite" in hits[0].text


async def test_stub_retriever_respects_top_k_zero() -> None:
    retriever = StubRetriever()
    assert await retriever.retrieve("q", RuleType.STIMULATION, 0) == []
