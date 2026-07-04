"""Postgres + pgvector backend (the fallback store).

Coded fully but never exercised on the offline path: ``psycopg`` ships in the ``live`` extra, so its
import is lazy and typing-guarded. Text queries are embedded once via the Vultr retriever, then
scored in-database with pgvector's cosine-distance operator (``<=>``) filtered by ``rule_type``.

Expected schema (owned by the indexing job, not this lane)::

    CREATE TABLE corpus_pages (
        doc_id     text,
        rule_type  text,
        page       int,
        article    text,
        text       text,
        embedding  vector(N)
    );
"""

from __future__ import annotations

from cyclesentinel.config import Settings
from cyclesentinel.enums import RuleType
from cyclesentinel.retrieval.store import Query
from cyclesentinel.retrieval.vultr_store import embed_query
from cyclesentinel.schemas import RetrievalHit

_SEARCH_SQL = """
SELECT doc_id, rule_type, page, article, text,
       1 - (embedding <=> %(vec)s::vector) AS score
FROM corpus_pages
WHERE rule_type = %(rule_type)s
ORDER BY embedding <=> %(vec)s::vector
LIMIT %(top_k)s
"""


def _vector_literal(vec: list[float]) -> str:
    """Render an embedding as a pgvector literal, e.g. ``[0.1,0.2,0.3]``."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


class PgVectorStore:
    """Retrieval-only :class:`~cyclesentinel.retrieval.store.VectorStore` over Postgres/pgvector."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def query(self, rule_type: RuleType, query: Query, top_k: int = 3) -> list[RetrievalHit]:
        """Embed ``query`` if needed, then cosine-rank ``corpus_pages`` for ``rule_type``."""
        import psycopg  # type: ignore[import-not-found]  # 'live' extra only

        vec = query if isinstance(query, list) else embed_query(self._settings, query)
        params = {
            "vec": _vector_literal(vec),
            "rule_type": str(rule_type),
            "top_k": max(top_k, 0),
        }
        hits: list[RetrievalHit] = []
        with psycopg.connect(self._settings.database_url) as conn, conn.cursor() as cur:
            cur.execute(_SEARCH_SQL, params)
            for row in cur.fetchall():
                doc_id, rt, page, article, text, score = row
                hits.append(
                    RetrievalHit(
                        doc_id=str(doc_id),
                        rule_type=RuleType(str(rt)),
                        page=int(page),
                        score=float(score),
                        text=str(text),
                        article=str(article),
                    )
                )
        return hits
