"""Tests for the offline vector store + factory (no network, deterministic scoring)."""

from __future__ import annotations

from cyclesentinel.config import Settings
from cyclesentinel.enums import RuleType
from cyclesentinel.retrieval.local_store import LocalNumpyStore
from cyclesentinel.retrieval.store import CorpusRecord, VectorStore, get_vector_store

_CORPUS = [
    CorpusRecord(
        doc_id="ohss_sop",
        rule_type=RuleType.OHSS,
        page=4,
        article="§4.2",
        text="Coasting is indicated when estradiol rises steeply with many follicles OHSS risk.",
    ),
    CorpusRecord(
        doc_id="ohss_sop",
        rule_type=RuleType.OHSS,
        page=5,
        article="§4.3",
        text="Trigger swap to a GnRH agonist reduces ovarian hyperstimulation syndrome severity.",
    ),
    CorpusRecord(
        doc_id="luteinization_rule",
        rule_type=RuleType.LUTEINIZATION,
        page=2,
        article="§2.1",
        text="Progesterone elevated for the cycle day suggests premature luteinization freeze-all.",
    ),
]


def test_local_store_filters_by_rule_type() -> None:
    store = LocalNumpyStore(_CORPUS)
    hits = store.query(RuleType.LUTEINIZATION, "progesterone elevated luteinization", top_k=5)
    assert len(hits) == 1
    assert hits[0].doc_id == "luteinization_rule"
    assert all(h.rule_type == RuleType.LUTEINIZATION for h in hits)


def test_local_store_lexical_ranking_and_top_k() -> None:
    store = LocalNumpyStore(_CORPUS)
    hits = store.query(RuleType.OHSS, "coasting steeply estradiol follicles", top_k=1)
    assert len(hits) == 1
    # The coasting page shares the most tokens with the query.
    assert hits[0].page == 4
    assert hits[0].score > 0.0


def test_local_store_vector_query_uses_cosine() -> None:
    corpus = [
        CorpusRecord(
            doc_id="d",
            rule_type=RuleType.OHSS,
            page=1,
            article="a1",
            text="x",
            embedding=[1.0, 0.0],
        ),
        CorpusRecord(
            doc_id="d",
            rule_type=RuleType.OHSS,
            page=2,
            article="a2",
            text="y",
            embedding=[0.0, 1.0],
        ),
    ]
    store = LocalNumpyStore(corpus)
    hits = store.query(RuleType.OHSS, [0.9, 0.1], top_k=2)
    assert hits[0].page == 1  # closest to the query vector
    assert hits[0].score > hits[1].score


def test_local_store_empty_when_no_match() -> None:
    store = LocalNumpyStore(_CORPUS)
    assert store.query(RuleType.POOR_RESPONDER, "flat response", top_k=3) == []


def test_get_vector_store_local_default() -> None:
    settings = Settings()  # default vector_store == "local" (offline path)
    assert settings.vector_store == "local"
    store = get_vector_store(settings, corpus=_CORPUS)
    assert isinstance(store, LocalNumpyStore)
    # Satisfies the VectorStore Protocol.
    assert isinstance(store, VectorStore)
    assert store.query(RuleType.OHSS, "coasting", top_k=1)[0].doc_id == "ohss_sop"
