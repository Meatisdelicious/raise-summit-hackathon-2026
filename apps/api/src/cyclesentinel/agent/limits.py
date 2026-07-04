"""Run guardrails: the step budget and the schema-retry policy.

Both are deliberately small. :class:`StepBudget` caps the number of logical agent steps per run
(``<= 10`` per ``docs/doc.md`` §2) and raises :class:`StepBudgetError` if the loop ever tries to
take more — a runaway trap, never hit by the four demo cases. :class:`RetryPolicy` says how many
times a schema-validated LLM turn (the plan, the brief) may be re-attempted before the run degrades
to ``AMBIGUOUS_REQUIRES_REVIEW`` (raised as :class:`AgentAmbiguousError`).
"""

from __future__ import annotations

from dataclasses import dataclass


class StepBudgetError(RuntimeError):
    """Raised when a run tries to take more logical steps than its :class:`StepBudget` allows."""


class AgentAmbiguousError(RuntimeError):
    """Raised when the run cannot be resolved deterministically (bad model output / grounding).

    The loop catches this and finishes with ``AMBIGUOUS_REQUIRES_REVIEW`` — never a silent
    "normal" (the fail-safe posture in ``docs/doc.md`` §4).
    """


@dataclass
class StepBudget:
    """A monotonic counter of logical agent steps, capped at ``max_steps``.

    A *step* is a coarse pipeline stage (plan, each context/trajectory read, the whole compute
    phase, each conditional rule retrieval, the action, the brief) — not every emitted event. The
    demo cases spend well under the cap; the budget only fires on a pathological loop.
    """

    max_steps: int = 10
    used: int = 0

    def spend(self, n: int = 1) -> int:
        """Spend ``n`` steps and return the new total, raising if it exceeds ``max_steps``."""
        self.used += n
        if self.used > self.max_steps:
            raise StepBudgetError(f"step budget exhausted: {self.used} > {self.max_steps}")
        return self.used

    def remaining(self) -> int:
        """Return how many steps are still available."""
        return self.max_steps - self.used


@dataclass(frozen=True)
class RetryPolicy:
    """How many times to re-attempt a schema-validated LLM turn before giving up.

    ``retries=1`` means one initial attempt plus one retry (two total), then
    :class:`AgentAmbiguousError`.
    """

    retries: int = 1

    @property
    def attempts(self) -> int:
        """Total attempts allowed (initial + retries)."""
        return self.retries + 1
