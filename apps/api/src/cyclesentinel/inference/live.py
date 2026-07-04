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

import httpx
from pydantic import BaseModel, Field

from cyclesentinel.config import Settings
from cyclesentinel.enums import RuleType
from cyclesentinel.inference.base import ChatMessage, ChatResponse, ToolCall, ToolSchema
from cyclesentinel.schemas import RetrievalHit

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


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


# --- Wire DTOs: retrieval-only vector-store search ---------------------------------------------


class _WireRetrievalItem(BaseModel):
    """One scored item from the vector-store search response.

    Field names are mapped defensively: the page text may arrive as ``text``/``content``/``chunk``,
    and page/article/doc_id/rule_type live in an item ``metadata`` object we control at index time.
    """

    text: str | None = None
    content: str | None = None
    chunk: str | None = None
    score: float = 0.0
    metadata: dict[str, object] = Field(default_factory=dict)

    def page_text(self) -> str:
        """Best-available page text layer (what the text-only LLM reads to cite the article)."""
        return self.text or self.content or self.chunk or ""


class _WireRetrievalResponse(BaseModel):
    items: list[_WireRetrievalItem] = Field(default_factory=list)


def _meta_str(meta: dict[str, object], key: str, default: str = "") -> str:
    value = meta.get(key)
    return value if isinstance(value, str) else default


def _meta_int(meta: dict[str, object], key: str, default: int = 0) -> int:
    value = meta.get(key)
    if isinstance(value, bool):  # bool is an int subclass — reject it explicitly
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


class VultrPrimeRetriever:
    """Vultron Prime-8B visual document retrieval over the Vultr Vector Store (retrieval-only)."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.vultr_inference_base_url.rstrip("/")
        self._api_key = settings.vultr_inference_api_key
        self._model = settings.cs_retriever_model
        self._collection = settings.vultr_vector_collection

    async def retrieve(self, query: str, rule_type: RuleType, top_k: int) -> list[RetrievalHit]:
        """Search the collection for ``query``, filtered to ``rule_type``, and return scored pages.

        Retrieval-only: this returns pages + scores; generation stays in :class:`VultrLLMClient`. We
        never call ``/chat/completions/RAG`` (which would fuse retrieval and generation).
        """
        payload: dict[str, object] = {
            "model": self._model,
            "query": query,
            "top_k": top_k,
            "filter": {"rule_type": str(rule_type)},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/vector_store/{self._collection}/search"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            body: object = resp.json()
        wire = _WireRetrievalResponse.model_validate(body)
        hits = [
            RetrievalHit(
                doc_id=_meta_str(item.metadata, "doc_id"),
                rule_type=rule_type,
                page=_meta_int(item.metadata, "page"),
                score=item.score,
                text=item.page_text(),
                article=_meta_str(item.metadata, "article"),
            )
            for item in wire.items
            if _meta_str(item.metadata, "rule_type", str(rule_type)) == str(rule_type)
        ]
        return hits[:top_k]
