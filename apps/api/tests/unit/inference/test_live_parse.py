"""Live-path wire parsing (no network): OpenAI-compatible responses map to our DTOs correctly."""

from __future__ import annotations

from cyclesentinel.inference.live import (
    _first_article,
    _parse_arguments,
    _to_chat_response,
    _WireSearchResponse,
)


def test_parse_chat_response_with_tool_calls() -> None:
    body = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "type": "function",
                            "function": {
                                "name": "compute_ohss_composite",
                                "arguments": '{"e2": 4200, "pcos": true}',
                            },
                        }
                    ],
                }
            }
        ]
    }
    resp = _to_chat_response(body)
    assert resp.content is None
    assert len(resp.tool_calls) == 1
    tc = resp.tool_calls[0]
    assert tc.id == "call_abc"
    assert tc.name == "compute_ohss_composite"
    assert tc.arguments == {"e2": 4200, "pcos": True}


def test_parse_chat_response_plain_content() -> None:
    body = {"choices": [{"message": {"content": "routine, continue protocol"}}]}
    resp = _to_chat_response(body)
    assert resp.content == "routine, continue protocol"
    assert resp.tool_calls == []


def test_parse_chat_response_no_choices() -> None:
    resp = _to_chat_response({"choices": []})
    assert resp.content is None
    assert resp.tool_calls == []


def test_parse_arguments_tolerates_bad_json() -> None:
    assert _parse_arguments("not json") == {}
    assert _parse_arguments("") == {}
    assert _parse_arguments("[1,2,3]") == {}  # array, not an object
    assert _parse_arguments('{"k": 1}') == {"k": 1}


def test_search_response_parses_results_content() -> None:
    # Real Vultr shape: {"results": [{"id", "content"}]} — no score, no metadata.
    wire = _WireSearchResponse.model_validate(
        {"results": [{"id": "x", "content": "§4.2 OHSS escalation guidance"}]}
    )
    assert len(wire.results) == 1
    assert wire.results[0].content == "§4.2 OHSS escalation guidance"


def test_search_response_empty_when_no_results() -> None:
    assert _WireSearchResponse.model_validate({}).results == []


def test_first_article_extracts_section_label() -> None:
    assert _first_article("§4.2 OHSS escalation and management\n...") == "§4.2"
    assert _first_article("§ 2.3 Cycle-day thresholds") == "§2.3"
    assert _first_article("no article here") == ""
