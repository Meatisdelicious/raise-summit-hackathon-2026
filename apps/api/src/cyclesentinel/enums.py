"""Frozen enumerations — values mirror ``docs/CONTRACTS.md`` §1 byte-for-byte.

These are :class:`~enum.StrEnum` members so they serialize to their exact string values in JSON and
match the TypeScript literal unions the frontend consumes.
"""

from __future__ import annotations

from enum import StrEnum


class Protocol(StrEnum):
    """Ovarian-stimulation protocol type."""

    ANTAGONIST = "antagonist"
    LONG_AGONIST = "long_agonist"
    SHORT_AGONIST = "short_agonist"
    OTHER = "other"


class DecisionState(StrEnum):
    """Constrained set of escalation/decision states a run may raise (may hold >1)."""

    ROUTINE_CONTINUE = "ROUTINE_CONTINUE"
    OHSS_RISK_ESCALATE = "OHSS_RISK_ESCALATE"
    PREMATURE_LUTEINIZATION_FLAG = "PREMATURE_LUTEINIZATION_FLAG"
    POOR_RESPONSE_FLAG = "POOR_RESPONSE_FLAG"
    MISSING_TIMEPOINT = "MISSING_TIMEPOINT"
    AMBIGUOUS_REQUIRES_REVIEW = "AMBIGUOUS_REQUIRES_REVIEW"


class EscalationLevel(StrEnum):
    """Severity of the escalation attached to a brief."""

    NONE = "none"
    INFO = "info"
    URGENT = "urgent"


class RuleType(StrEnum):
    """Which governing protocol/SOP rule a conditional retrieval targets."""

    OHSS = "ohss"
    LUTEINIZATION = "luteinization"
    POOR_RESPONDER = "poor_responder"
    STIMULATION = "stimulation"
