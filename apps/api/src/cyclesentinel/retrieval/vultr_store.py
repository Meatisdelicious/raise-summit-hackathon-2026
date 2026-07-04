"""Vultr Vector Store backend (EU region) — the demo store.

Coded fully but never exercised on the offline path. Text queries are embedded once via the Vultr
retriever (Vultron Prime-8B) over the OpenAI-compatible ``/embeddings`` endpoint, then the Vultr
Vector Store is queried in **retrieval-only** mode (we never call the one-shot RAG endpoint — that
would collapse the agent loop). ``embed_query`` is shared with the pgvector fallback.
"""

from __future__ import annotations

import httpx

from cyclesentinel.config import Settings
from cyclesentinel.enums import RuleType
from cyclesentinel.retrieval.store import Query
from cyclesentinel.schemas import RetrievalHit

_TIMEOUT = httpx.Timeout(30.0)


def _auth_headers(settings: Settings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.vultr_inference_api_key}",
        "Content-Type": "application/json",
    }


def embed_query(settings: Settings, text: str) -> list[float]:
    """Embed ``text`` with the configured retriever model; return the embedding vector.

    Uses the OpenAI-compatible ``POST {base_url}/embeddings`` shape. Raises if the response does not
    contain a usable embedding.
    """
    url = f"{settings.vultr_inference_base_url.rstrip('/')}/embeddings"
    body = {"model": settings.cs_retriever_model, "input": text}
    resp = httpx.post(url, headers=_auth_headers(settings), json=body, timeout=_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        embedding = data[0].get("embedding")
        if isinstance(embedding, list):
            return [float(x) for x in embedding]
    raise ValueError("Vultr embeddings response contained no embedding vector")


class VultrVectorStore:
    """Retrieval-only store over Vultr Vector Store (EU), queried in retrieval-only mode."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _search_url(self) -> str:
        base = self._settings.vultr_inference_base_url.rstrip("/")
        collection = self._settings.vultr_vector_collection
        return f"{base}/vector-stores/{collection}/search"

    def query(self, rule_type: RuleType, query: Query, top_k: int = 3) -> list[RetrievalHit]:
        """Embed ``query`` if needed, then fetch top-k pages for ``rule_type`` (retrieval-only)."""
        vec = query if isinstance(query, list) else embed_query(self._settings, query)
        body = {
            "query_embedding": vec,
            "top_k": max(top_k, 0),
            "filter": {"rule_type": str(rule_type)},
        }
        resp = httpx.post(
            self._search_url(), headers=_auth_headers(self._settings), json=body, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        payload = resp.json()
        raw_hits = payload.get("hits") if isinstance(payload, dict) else None
        if not isinstance(raw_hits, list):
            return []
        return [_parse_hit(item) for item in raw_hits if isinstance(item, dict)]


def _parse_hit(item: dict[str, object]) -> RetrievalHit:
    return RetrievalHit(
        doc_id=str(item.get("doc_id", "")),
        rule_type=RuleType(str(item.get("rule_type", RuleType.STIMULATION))),
        page=int(_as_number(item.get("page"))),
        score=float(_as_number(item.get("score"))),
        text=str(item.get("text", "")),
        article=str(item.get("article", "")),
    )


def _as_number(value: object) -> float:
    """Coerce a JSON scalar to ``float`` (0.0 when missing/non-numeric)."""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0
