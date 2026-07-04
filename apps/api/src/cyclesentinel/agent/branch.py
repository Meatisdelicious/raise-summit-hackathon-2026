"""The "not RAG" core: map tripped computed signals to which rule(s) to retrieve.

:func:`branches_for` is a pure function — the *only* path by which the agent reaches conditional
retrieval. If nothing tripped it returns an empty list and the run performs no ``retrieve_rule``
(the routine control case). This is what makes retrieval computation-driven rather than a fixed
pipeline step (``docs/doc.md`` §3, hard rule 4).
"""

from __future__ import annotations

from collections.abc import Sequence

from cyclesentinel.enums import RuleType
from cyclesentinel.schemas import ComputedSignal

# Which tripped signal opens which rule branch (order fixes the retrieval order in the trace).
_SIGNAL_TO_RULE: tuple[tuple[str, RuleType], ...] = (
    ("ohss_composite", RuleType.OHSS),
    ("progesterone_for_day", RuleType.LUTEINIZATION),
    ("response_curve", RuleType.POOR_RESPONDER),
)


def _tripped(signals: Sequence[ComputedSignal], name: str) -> bool:
    """True if the signal named ``name`` is present and tripped."""
    return any(s.name == name and s.tripped for s in signals)


def branches_for(signals: Sequence[ComputedSignal]) -> list[RuleType]:
    """Return the rule types to retrieve, in order, for the tripped signals (empty if none).

    Each rule appears at most once (each signal maps to one rule and is checked once), so a case
    never retrieves the same rule twice — satisfying the "each conditional rule retrieved at most
    once" constraint (``docs/doc.md`` §2).
    """
    return [rule for name, rule in _SIGNAL_TO_RULE if _tripped(signals, name)]
