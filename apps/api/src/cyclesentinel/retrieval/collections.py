"""Per-``rule_type`` Vultr Vector Store collection ids (shared by the indexer and the retriever).

The store has no server-side ``rule_type`` filter, so conditional retrieval uses one collection per
rule_type: the branch queries exactly the collection for the rule it needs. Vultr derives an id from
the name by stripping non-alphanumerics and truncating to 14 chars, so we build ids that are already
valid (short, alphanumeric, distinct): ``cs`` + a per-rule abbreviation. Both the indexer
(``scripts/index_corpus.py``) and the live retriever call :func:`collection_id` so they can't drift.
"""

from __future__ import annotations

from cyclesentinel.enums import RuleType

# Distinct first letters keep the ids unique even after Vultr's 14-char truncation.
_ABBREV: dict[RuleType, str] = {
    RuleType.OHSS: "ohss",
    RuleType.LUTEINIZATION: "lut",
    RuleType.POOR_RESPONDER: "poor",
    RuleType.STIMULATION: "stim",
}

_MAX_ID_LEN = 14


def collection_id(prefix: str, rule_type: RuleType) -> str:
    """Return the Vultr collection id for ``rule_type`` under ``prefix`` (alphanumeric, <=14)."""
    raw = f"{prefix}{_ABBREV[rule_type]}"
    return "".join(ch for ch in raw if ch.isalnum())[:_MAX_ID_LEN]
