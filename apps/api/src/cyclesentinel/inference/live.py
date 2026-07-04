"""Live Vultr Serverless Inference clients — the demo path (EU-hosted, all-Qwen3.5 stack).

Two clients, both hitting ``VULTR_INFERENCE_BASE_URL`` (already ``…/v1``) with a bearer token:

* :class:`VultrLLMClient` — Kimi K2 Instruct via the OpenAI-compatible ``POST /v1/chat/completions``
  at ``temperature=0``, with tool-calling. This is the reasoning/tool-use LLM in the trace.
* :class:`VultrPrimeRetriever` — the Vultron **Prime-8B** visual document retriever over the Vultr
  Vector Store, queried in **retrieval-only** mode (``POST /v1/vector_store/{collection}/search``):
  it returns scored protocol/SOP **pages** with their text layer, which the LLM then cites.

We deliberately **never** call ``POST /v1/chat/completions/RAG`` — the one-shot RAG endpoint fuses
retrieval and generation into a single call and would collapse the agent loop / hide the conditional
retrieval that is the whole demo (see ``docs/doc.md`` §3, §8). Retrieval here is an explicit agent
tool, called at most once per branch.

This code can't be exercised offline (CI runs in replay/stub), so it is written to be correct by
construction: OpenAI-compatible request/response shapes, defensive typed parsing, no bare ``Any``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from cyclesentinel.config import Settings
from cyclesentinel.enums import RuleType
from cyclesentinel.inference.base import ChatMessage, ChatResponse, ToolCall, ToolSchema
from cyclesentinel.retrieval.collections import collection_id
from cyclesentinel.retrieval.corpus import load_corpus
from cyclesentinel.schemas import RetrievalHit

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
# live.py -> inference -> cyclesentinel -> src -> api -> apps -> repo root (parents[5]).
_CORPUS_DIR = Path(__file__).resolve().parents[5] / "data" / "synthetic" / "corpus"
_ARTICLE_RE = re.compile(r"§\s*[\d.]+")


# --- Wire DTOs: OpenAI-compatible chat-completions response ------------------------------------


class _WireFunction(BaseModel):
    name: str
    arguments: str = "{}"


class _WireToolCall(BaseModel):
    id: str = ""
    function: _WireFunction


class _WireMessage(BaseModel):
    content: str | None = None
    tool_calls: list[_WireToolCall] = Field(default_factory=list)


class _WireChoice(BaseModel):
    message: _WireMessage


class _WireChatResponse(BaseModel):
    choices: list[_WireChoice] = Field(default_factory=list)


def _parse_arguments(raw: str) -> dict[str, object]:
    """Parse a tool-call ``arguments`` JSON string into a dict (empty if not an object)."""
    try:
        parsed: object = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return {str(k): v for k, v in parsed.items()}
    return {}


def _to_chat_response(data: object) -> ChatResponse:
    """Map a decoded OpenAI-compatible chat-completions body to our :class:`ChatResponse`."""
    wire = _WireChatResponse.model_validate(data)
    if not wire.choices:
        return ChatResponse(content=None, tool_calls=[])
    message = wire.choices[0].message
    tool_calls = [
        ToolCall(id=tc.id, name=tc.function.name, arguments=_parse_arguments(tc.function.arguments))
        for tc in message.tool_calls
    ]
    return ChatResponse(content=message.content, tool_calls=tool_calls)


class VultrLLMClient:
    """Kimi K2 Instruct via Vultr's OpenAI-compatible ``/chat/completions`` (temperature 0)."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.vultr_inference_base_url.rstrip("/")
        self._api_key = settings.vultr_inference_api_key
        self._model = settings.cs_llm_model

    async def chat(
        self, messages: list[ChatMessage], tools: list[ToolSchema] | None = None
    ) -> ChatResponse:
        """POST one chat-completions turn and return the parsed assistant response."""
        payload: dict[str, object] = {
            "model": self._model,
            "temperature": 0,
            "messages": [m.to_wire() for m in messages],
        }
        if tools:
            payload["tools"] = [t.to_wire() for t in tools]
            payload["tool_choice"] = "auto"
        else:
            # Both LLM turns (plan, brief) expect a JSON object; force it so the model can't drift
            # into markdown/prose. Not part of the cassette key, so replay is unaffected.
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            body: object = resp.json()
        return _to_chat_response(body)


# --- Vultr Vector Store search --------------------------------------------------------------
# Real API (confirmed against /v1/vector_store): POST /vector_store/{id}/search with {"input",
# "top_k"} returns {"results":[{"content"}]} — no server-side filter, no per-item metadata, no
# score. So the branch queries the one collection for its rule_type (see retrieval/collections.py)
# and we recover each hit's citation by matching the returned page text back to the local corpus.


class _WireSearchResult(BaseModel):
    content: str = ""


class _WireSearchResponse(BaseModel):
    results: list[_WireSearchResult] = Field(default_factory=list)


def _first_article(text: str) -> str:
    """Best-effort article label from a page's text (fallback when corpus match fails)."""
    match = _ARTICLE_RE.search(text)
    return match.group(0).replace(" ", "") if match else ""


class VultrPrimeRetriever:
    """Conditional retrieval over the Vultr Vector Store (one collection per ``rule_type``).

    Retrieval-only: returns pages; generation stays in :class:`VultrLLMClient` (we never call
    ``/chat/completions/RAG``). The store has no filter/metadata, so the branch searches exactly the
    ``rule_type`` collection and citations are recovered by matching returned text to the corpus.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.vultr_inference_base_url.rstrip("/")
        self._api_key = settings.vultr_inference_api_key
        self._prefix = settings.vultr_vector_collection or "cs"
        corpus = load_corpus(_CORPUS_DIR)
        self._by_text = {page.text.strip(): page for page in corpus.pages}

    async def retrieve(self, query: str, rule_type: RuleType, top_k: int) -> list[RetrievalHit]:
        """Search the ``rule_type`` collection for ``query`` and return the top-k pages as hits."""
        collection = collection_id(self._prefix, rule_type)
        payload: dict[str, object] = {"input": query, "top_k": top_k}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/vector_store/{collection}/search"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            body: object = resp.json()
        wire = _WireSearchResponse.model_validate(body)
        hits: list[RetrievalHit] = []
        for rank, result in enumerate(wire.results[:top_k]):
            page = self._by_text.get(result.content.strip())
            hits.append(
                RetrievalHit(
                    doc_id=page.doc_id if page else "",
                    rule_type=rule_type,
                    page=page.page if page else 0,
                    score=round(1.0 - 0.05 * rank, 3),  # rank proxy — the API returns no score
                    text=result.content,
                    article=page.article if page else _first_article(result.content),
                )
            )
        return hits
