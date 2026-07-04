"""Live Vultr Serverless Inference clients — the demo path (EU-hosted, all-Qwen3.5 stack).

Two clients, both hitting ``VULTR_INFERENCE_BASE_URL`` (already ``…/v1``) with a bearer token:

* :class:`VultrLLMClient` — Kimi K2 Instruct via the OpenAI-compatible ``POST /v1/chat/completions``
  at ``temperature=0``, with tool-calling. This is the reasoning/tool-use LLM in the trace.
* :class:`VultrPrimeRetriever` — two-stage retrieval-only: dense recall from the Vultr Vector Store
  (``POST /v1/vector_store/{id}/search``) then **Vultron Prime-8B** rerank (``POST /v1/rerank``),
  which scores the query against the candidate protocol/SOP pages and picks the governing one.

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


# --- Vultr retrieval: Vector Store recall + Vultron rerank --------------------------------------
# Two confirmed endpoints:
#   POST /vector_store/{id}/search  {"input","top_k"}  -> {"results":[{"content"}]}   (dense recall;
#       the store embeds internally — no metadata, no score; ``model`` on the request is ignored).
#   POST /rerank  {"model","query","documents":[...]}  -> {"results":[{index,relevance_score}]}
#       -> this is where Vultron Prime-8B (a cross-encoder retriever/reranker) actually scores the
#          query against the candidate pages and picks the governing one.
# So the branch: recall the rule_type collection, then rerank with Vultron; the top page is the
# citation, recovered by matching the returned text back to the local corpus.

_RECALL_K = 6  # over-fetch for the reranker; the per-rule corpus is small, so this covers it.


class _WireSearchResult(BaseModel):
    content: str = ""


class _WireSearchResponse(BaseModel):
    results: list[_WireSearchResult] = Field(default_factory=list)


class _WireRerankResult(BaseModel):
    index: int = 0
    relevance_score: float = 0.0


class _WireRerankResponse(BaseModel):
    results: list[_WireRerankResult] = Field(default_factory=list)


def _first_article(text: str) -> str:
    """Best-effort article label from a page's text (fallback when corpus match fails)."""
    match = _ARTICLE_RE.search(text)
    return match.group(0).replace(" ", "") if match else ""


class VultrPrimeRetriever:
    """Conditional retrieval: Vultr Vector Store recall + **Vultron Prime-8B** rerank.

    Retrieval-only (generation stays in :class:`VultrLLMClient`; we never call ``/chat/completions/
    RAG``). The branch recalls exactly its ``rule_type`` collection, then Vultron reranks the
    candidate pages to pick the governing article; citations are recovered against the local corpus.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.vultr_inference_base_url.rstrip("/")
        self._api_key = settings.vultr_inference_api_key
        self._prefix = settings.vultr_vector_collection or "cs"
        self._model = settings.cs_retriever_model  # Vultron Prime-8B — actually used, for rerank
        corpus = load_corpus(_CORPUS_DIR)
        self._by_text = {page.text.strip(): page for page in corpus.pages}

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def _recall(self, client: httpx.AsyncClient, collection: str, query: str) -> list[str]:
        """Dense recall from the Vector Store: return candidate page texts (verbatim)."""
        url = f"{self._base_url}/vector_store/{collection}/search"
        resp = await client.post(
            url, json={"input": query, "top_k": _RECALL_K}, headers=self._headers
        )
        resp.raise_for_status()
        wire = _WireSearchResponse.model_validate(resp.json())
        return [r.content for r in wire.results]

    async def _rerank(
        self, client: httpx.AsyncClient, query: str, docs: list[str]
    ) -> list[tuple[str, float]]:
        """Rerank ``docs`` vs ``query`` with Vultron Prime-8B; return (text, score) best-first."""
        resp = await client.post(
            f"{self._base_url}/rerank",
            json={"model": self._model, "query": query, "documents": docs},
            headers=self._headers,
        )
        resp.raise_for_status()
        wire = _WireRerankResponse.model_validate(resp.json())
        ranked = [
            (docs[r.index], r.relevance_score) for r in wire.results if 0 <= r.index < len(docs)
        ]
        return ranked or [(d, 0.0) for d in docs]  # fall back to recall order on an empty rerank

    async def retrieve(self, query: str, rule_type: RuleType, top_k: int) -> list[RetrievalHit]:
        """Recall the ``rule_type`` collection, rerank with Vultron, return the top-k as hits."""
        collection = collection_id(self._prefix, rule_type)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            candidates = await self._recall(client, collection, query)
            if not candidates:
                return []
            ranked = await self._rerank(client, query, candidates)
        hits: list[RetrievalHit] = []
        for text, score in ranked[:top_k]:
            page = self._by_text.get(text.strip())
            hits.append(
                RetrievalHit(
                    doc_id=page.doc_id if page else "",
                    rule_type=rule_type,
                    page=page.page if page else 0,
                    score=round(score, 4),
                    text=text,
                    article=page.article if page else _first_article(text),
                )
            )
        return hits
