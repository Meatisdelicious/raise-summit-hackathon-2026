"""Vector-store seam for conditional protocol/SOP retrieval.

``retrieve_protocol_rule`` (Lane A tool) calls a :class:`VectorStore` to fetch the top-k protocol
pages for a ``rule_type``. Three interchangeable backends, chosen by ``settings.vector_store``:

* ``local``   — :class:`~cyclesentinel.retrieval.local_store.LocalNumpyStore`, offline dev/CI.
* ``pgvector`` — Postgres + pgvector (``live`` extra), the fallback store.
* ``vultr``    — Vultr Vector Store (EU), retrieval-only, the demo store.

The query may be raw text (the retriever embeds it) or a precomputed embedding vector.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from cyclesentinel.config import Settings
from cyclesentinel.enums import RuleType
from cyclesentinel.schemas import RetrievalHit

# A retrieval query is either the raw question text or a precomputed embedding vector.
Query = str | list[float]


class CorpusRecord(BaseModel):
    """One indexed protocol/SOP page: its text layer, visible article label, and page embedding.

    Lane D's ``retrieval/corpus.py`` is expected to expose ``load_corpus() -> list[CorpusRecord]``
    (or a list of dicts with these fields); ``embedding`` is Prime-8B's page-image vector, absent in
    the fully offline path where :class:`LocalNumpyStore` falls back to lexical scoring.
    """

    model_config = ConfigDict(use_enum_values=True)

    doc_id: str
    rule_type: RuleType
    page: int
    article: str
    text: str
    embedding: list[float] | None = None


@runtime_checkable
class VectorStore(Protocol):
    """Retrieval-only store: score the corpus for one ``rule_type`` and return top-k pages."""

    def query(self, rule_type: RuleType, query: Query, top_k: int = 3) -> list[RetrievalHit]:
        """Return up to ``top_k`` :class:`RetrievalHit`s for ``rule_type``, best score first."""
        ...


def get_vector_store(settings: Settings, corpus: list[CorpusRecord] | None = None) -> VectorStore:
    """Construct the configured :class:`VectorStore`.

    ``corpus`` (when given) seeds the offline ``local`` store directly; otherwise the local store is
    empty until Lane D's corpus is wired in. The ``pgvector`` / ``vultr`` backends are imported
    lazily so their optional dependencies never load on the offline path.
    """
    backend = settings.vector_store
    if backend == "pgvector":
        from cyclesentinel.retrieval.pgvector_store import PgVectorStore

        return PgVectorStore(settings)
    if backend == "vultr":
        from cyclesentinel.retrieval.vultr_store import VultrVectorStore

        return VultrVectorStore(settings)

    from cyclesentinel.retrieval.local_store import LocalNumpyStore

    return LocalNumpyStore(corpus or [])
