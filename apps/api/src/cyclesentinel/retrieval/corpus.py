"""Synthetic protocol/SOP corpus loader.

The corpus lives under ``data/synthetic/corpus/<doc_id>/`` as one triple per page:
``page-NN.txt`` (the text layer the text-only LLM cites), ``page-NN.meta.json``
(``{doc_id, rule_type, page, article}``) and an optional ``page-NN.png`` placeholder image (the
layer the visual retriever, Vultron Prime-8B, embeds).

This module reads those files into a typed :class:`Corpus`. It performs no retrieval scoring here —
the retriever client ranks pages; we only load, look up page text, and filter by ``rule_type``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cyclesentinel.enums import RuleType


@dataclass(frozen=True, slots=True)
class CorpusPage:
    """One page of the synthetic corpus: its text layer, metadata, and optional image path."""

    doc_id: str
    rule_type: RuleType
    page: int
    article: str
    text: str
    image_path: Path | None = None


@dataclass(frozen=True, slots=True)
class Corpus:
    """An immutable collection of loaded corpus pages with simple lookups."""

    pages: tuple[CorpusPage, ...]

    def get_page_text(self, doc_id: str, page: int) -> str:
        """Return the text layer for one page, or raise ``KeyError`` if it is not in the corpus."""
        for candidate in self.pages:
            if candidate.doc_id == doc_id and candidate.page == page:
                return candidate.text
        raise KeyError(f"no corpus page for doc_id={doc_id!r} page={page}")

    def filter_by(self, rule_type: RuleType) -> tuple[CorpusPage, ...]:
        """Return the pages whose ``rule_type`` matches (the retrieval filter), page-ordered."""
        return tuple(page for page in self.pages if page.rule_type == rule_type)

    def doc_ids(self) -> tuple[str, ...]:
        """Return the distinct ``doc_id`` values, in first-seen order."""
        seen: list[str] = []
        for page in self.pages:
            if page.doc_id not in seen:
                seen.append(page.doc_id)
        return tuple(seen)


def _load_page(txt_path: Path) -> CorpusPage:
    """Load a single page from its ``page-NN.txt`` path (its ``.meta.json`` sits beside it)."""
    meta_path = txt_path.with_suffix(".meta.json")
    raw: object = json.loads(meta_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"malformed corpus meta (expected object): {meta_path}")
    meta: dict[str, object] = raw

    doc_id = meta["doc_id"]
    rule_type = meta["rule_type"]
    page = meta["page"]
    article = meta["article"]
    if not (isinstance(doc_id, str) and isinstance(rule_type, str) and isinstance(article, str)):
        raise ValueError(f"corpus meta has non-string field: {meta_path}")
    if not isinstance(page, int):
        raise ValueError(f"corpus meta 'page' must be an int: {meta_path}")

    image_path = txt_path.with_suffix(".png")
    return CorpusPage(
        doc_id=doc_id,
        rule_type=RuleType(rule_type),
        page=page,
        article=article,
        text=txt_path.read_text(encoding="utf-8"),
        image_path=image_path if image_path.exists() else None,
    )


def load_corpus(path: str | Path) -> Corpus:
    """Load every ``page-NN.txt`` under ``path`` (recursively) into a :class:`Corpus`.

    Pages are sorted by ``(doc_id, page)`` for deterministic ordering.
    """
    root = Path(path)
    if not root.is_dir():
        raise FileNotFoundError(f"corpus directory not found: {root}")

    pages = [
        _load_page(txt_path)
        for txt_path in root.rglob("page-*.txt")
        if not txt_path.name.endswith(".meta.json")
    ]
    pages.sort(key=lambda p: (p.doc_id, p.page))
    return Corpus(pages=tuple(pages))
