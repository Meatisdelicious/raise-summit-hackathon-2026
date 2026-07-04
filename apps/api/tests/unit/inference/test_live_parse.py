"""Live-path wire parsing (no network): OpenAI-compatible responses map to our DTOs correctly."""

from __future__ import annotations

from cyclesentinel.enums import RuleType
from cyclesentinel.inference.live import (
    _parse_arguments,
    _to_chat_response,
    _WireRetrievalItem,
    _WireRetrievalResponse,
)
from cyclesentinel.schemas import RetrievalHit


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


def test_retrieval_item_prefers_text_then_content_then_chunk() -> None:
    assert _WireRetrievalItem(text="a", content="b", chunk="c").page_text() == "a"
    assert _WireRetrievalItem(content="b", chunk="c").page_text() == "b"
    assert _WireRetrievalItem(chunk="c").page_text() == "c"
    assert _WireRetrievalItem().page_text() == ""


def test_retrieval_response_maps_metadata_to_hit() -> None:
    wire = _WireRetrievalResponse.model_validate(
        {
            "items": [
                {
                    "text": "OHSS coasting guidance",
                    "score": 0.87,
                    "metadata": {
                        "doc_id": "ohss-sop",
                        "page": "12",
                        "article": "§4.2",
                        "rule_type": "ohss",
                    },
                }
            ]
        }
    )
    item = wire.items[0]
    hit = RetrievalHit(
        doc_id="ohss-sop",
        rule_type=RuleType.OHSS,
        page=12,
        score=item.score,
        text=item.page_text(),
        article="§4.2",
    )
    assert hit.page == 12
    assert hit.text == "OHSS coasting guidance"
    assert hit.score == 0.87
