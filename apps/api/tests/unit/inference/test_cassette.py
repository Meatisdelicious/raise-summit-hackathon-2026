"""Cassette keying + storage: volatile fields ignored, real content matters, round-trip works."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from cyclesentinel.enums import RuleType
from cyclesentinel.inference.base import ChatMessage, ToolSchema
from cyclesentinel.inference.cassette import (
    Cassette,
    cassette_key,
    llm_request_key,
    retriever_request_key,
)


def test_cassette_key_ignores_volatile_fields() -> None:
    base = {"model": "kimi", "messages": [{"role": "user", "content": "hi"}]}
    with_noise = {
        "model": "kimi",
        "messages": [{"role": "user", "content": "hi"}],
        "run_id": "run-abc",
        "created_at": "2026-07-04T10:00:00Z",
        "id": "550e8400-e29b-41d4-a716-4466554400ab",
    }
    assert cassette_key(base) == cassette_key(with_noise)


def test_cassette_key_scrubs_uuid_and_timestamp_values() -> None:
    a = {"trace": "550e8400-e29b-41d4-a716-4466554400ab", "at": "2026-07-04T10:00:00"}
    b = {"trace": "ffffffff-e29b-41d4-a716-4466554400ab", "at": "1999-01-01T00:00:00"}
    assert cassette_key(a) == cassette_key(b)


def test_cassette_key_is_temperature_pinned() -> None:
    assert cassette_key({"model": "kimi", "temperature": 0.9}) == cassette_key({"model": "kimi"})


def test_cassette_key_changes_with_real_content() -> None:
    assert cassette_key({"q": "steep E2 rise"}) != cassette_key({"q": "flat E2 curve"})


def test_cassette_key_order_independent_for_dict_keys() -> None:
    assert cassette_key({"a": 1, "b": 2}) == cassette_key({"b": 2, "a": 1})


def test_llm_request_key_stable_across_tool_call_ids() -> None:
    messages = [ChatMessage(role="user", content="interpret this draw")]
    tools = [ToolSchema(name="compute_e2_rate", description="rate", parameters={})]
    # tool_call_id is volatile → messages carrying different ids key identically.
    m1 = [*messages, ChatMessage(role="tool", tool_call_id="call-0001", name="x", content="1")]
    m2 = [*messages, ChatMessage(role="tool", tool_call_id="call-9999", name="x", content="1")]
    assert llm_request_key(m1, tools, "kimi") == llm_request_key(m2, tools, "kimi")


def test_llm_request_key_distinguishes_model_and_tools() -> None:
    messages = [ChatMessage(role="user", content="hi")]
    tools = [ToolSchema(name="t", description="d", parameters={})]
    assert llm_request_key(messages, tools, "kimi") != llm_request_key(messages, None, "kimi")
    assert llm_request_key(messages, tools, "kimi") != llm_request_key(messages, tools, "other")


def test_retriever_request_key_distinguishes_ruletype_and_topk() -> None:
    base = retriever_request_key("OHSS risk", RuleType.OHSS, 3, "prime")
    assert base != retriever_request_key("OHSS risk", RuleType.LUTEINIZATION, 3, "prime")
    assert base != retriever_request_key("OHSS risk", RuleType.OHSS, 5, "prime")
    assert base == retriever_request_key("OHSS risk", RuleType.OHSS, 3, "prime")


def test_cassette_save_load_round_trip(tmp_path: Path) -> None:
    cassette = Cassette(tmp_path / "llm")
    payload = {"content": "hello", "tool_calls": []}
    key = "deadbeef"
    assert cassette.load(key) is None  # miss before save
    cassette.save(key, payload)
    assert cassette.load(key) == payload
    assert cassette.path_for(key) == tmp_path / "llm" / "deadbeef.json"


def test_scrub_handles_nested_and_datetime_serialized_values() -> None:
    # datetime serialized to ISO string inside a nested structure is neutralized.
    now = datetime(2026, 7, 4, 12, 0, 0).isoformat()
    later = datetime(2030, 1, 1, 0, 0, 0).isoformat()
    a = {"outer": {"drawn": now, "keep": "e2=1200"}}
    b = {"outer": {"drawn": later, "keep": "e2=1200"}}
    assert cassette_key(a) == cassette_key(b)
