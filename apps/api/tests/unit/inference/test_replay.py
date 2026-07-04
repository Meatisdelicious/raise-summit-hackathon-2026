"""Replay clients: a hit returns the recorded object; a miss raises loudly (no network call)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cyclesentinel.enums import RuleType
from cyclesentinel.inference.base import ChatMessage, ChatResponse, ToolCall
from cyclesentinel.inference.cassette import Cassette, llm_request_key, retriever_request_key
from cyclesentinel.inference.replay import CassetteMissError, ReplayLLMClient, ReplayRetriever
from cyclesentinel.schemas import RetrievalHit


async def test_replay_llm_hit_returns_recorded_response(tmp_path: Path) -> None:
    cassette = Cassette(tmp_path / "llm")
    messages = [ChatMessage(role="user", content="interpret day-8 draw")]
    key = llm_request_key(messages, None, "kimi")
    recorded = ChatResponse(
        content="OHSS composite trips",
        tool_calls=[ToolCall(id="call-1", name="compute_ohss_composite", arguments={"e2": 4200})],
    )
    cassette.save(key, recorded.model_dump())

    client = ReplayLLMClient(cassette, model="kimi")
    got = await client.chat(messages)
    assert got.content == "OHSS composite trips"
    assert got.tool_calls[0].name == "compute_ohss_composite"
    assert got.tool_calls[0].arguments == {"e2": 4200}


async def test_replay_llm_miss_raises(tmp_path: Path) -> None:
    client = ReplayLLMClient(Cassette(tmp_path / "llm"), model="kimi")
    with pytest.raises(CassetteMissError):
        await client.chat([ChatMessage(role="user", content="never recorded")])


async def test_replay_retriever_hit_truncates_to_top_k(tmp_path: Path) -> None:
    cassette = Cassette(tmp_path / "retriever")
    key = retriever_request_key("OHSS risk composite", RuleType.OHSS, 2, "prime")
    hits = [
        RetrievalHit(
            doc_id="ohss-sop",
            rule_type=RuleType.OHSS,
            page=p,
            score=0.9 - p / 100,
            text=f"page {p}",
            article=f"§{p}",
        )
        for p in (3, 4, 5)
    ]
    cassette.save(key, [h.model_dump() for h in hits])

    retriever = ReplayRetriever(cassette, model="prime")
    got = await retriever.retrieve("OHSS risk composite", RuleType.OHSS, 2)
    assert len(got) == 2
    assert got[0].page == 3
    assert got[0].rule_type == RuleType.OHSS


async def test_replay_retriever_miss_raises(tmp_path: Path) -> None:
    retriever = ReplayRetriever(Cassette(tmp_path / "retriever"), model="prime")
    with pytest.raises(CassetteMissError):
        await retriever.retrieve("unrecorded query", RuleType.LUTEINIZATION, 3)


async def test_replay_retriever_malformed_cassette_raises(tmp_path: Path) -> None:
    cassette = Cassette(tmp_path / "retriever")
    key = retriever_request_key("q", RuleType.POOR_RESPONDER, 1, "prime")
    cassette.save(key, {"not": "a list"})  # wrong shape on disk
    retriever = ReplayRetriever(cassette, model="prime")
    with pytest.raises(CassetteMissError):
        await retriever.retrieve("q", RuleType.POOR_RESPONDER, 1)
