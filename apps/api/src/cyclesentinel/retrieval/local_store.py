"""Offline, deterministic vector store for dev and CI.

Holds the corpus in memory and scores it without any network call. When the query is a precomputed
embedding vector and pages carry embeddings, it uses cosine similarity (numpy); otherwise it falls
back to a deterministic lexical overlap between the query text and each page's text layer. Good
enough to exercise the conditional-retrieval branch end-to-end in ``replay``/``stub`` modes.
"""

from __future__ import annotations

import re

import numpy as np

from cyclesentinel.enums import RuleType
from cyclesentinel.retrieval.store import CorpusRecord, Query
from cyclesentinel.schemas import RetrievalHit

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def _lexical_score(query_tokens: set[str], text: str) -> float:
    """Jaccard overlap of query tokens with the page's tokens (0.0–1.0, deterministic)."""
    page_tokens = _tokenize(text)
    if not query_tokens or not page_tokens:
        return 0.0
    intersection = query_tokens & page_tokens
    union = query_tokens | page_tokens
    return len(intersection) / len(union)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


class LocalNumpyStore:
    """In-memory :class:`~cyclesentinel.retrieval.store.VectorStore` backed by numpy scoring."""

    def __init__(self, corpus: list[CorpusRecord]) -> None:
        self._corpus = corpus

    def query(self, rule_type: RuleType, query: Query, top_k: int = 3) -> list[RetrievalHit]:
        """Score pages of ``rule_type`` and return the ``top_k`` best as :class:`RetrievalHit`s."""
        candidates = [r for r in self._corpus if str(r.rule_type) == str(rule_type)]
        if not candidates:
            return []

        scored: list[tuple[float, CorpusRecord]] = []
        if isinstance(query, list):
            query_vec = np.asarray(query, dtype=float)
            for record in candidates:
                if record.embedding is None:
                    scored.append((0.0, record))
                    continue
                record_vec = np.asarray(record.embedding, dtype=float)
                scored.append((_cosine(query_vec, record_vec), record))
        else:
            query_tokens = _tokenize(query)
            for record in candidates:
                scored.append((_lexical_score(query_tokens, record.text), record))

        scored.sort(key=lambda pair: (pair[0], -pair[1].page), reverse=True)
        top = scored[: max(top_k, 0)]
        return [
            RetrievalHit(
                doc_id=record.doc_id,
                rule_type=record.rule_type,
                page=record.page,
                score=round(score, 6),
                text=record.text,
                article=record.article,
            )
            for score, record in top
        ]
