"""``StepBudget`` and ``RetryPolicy`` guardrails."""

from __future__ import annotations

import pytest

from cyclesentinel.agent import RetryPolicy, StepBudget, StepBudgetError


def test_step_budget_allows_up_to_max() -> None:
    budget = StepBudget(max_steps=3)
    assert budget.spend() == 1
    assert budget.spend() == 2
    assert budget.spend() == 3
    assert budget.remaining() == 0


def test_step_budget_raises_when_exceeded() -> None:
    budget = StepBudget(max_steps=2)
    budget.spend()
    budget.spend()
    with pytest.raises(StepBudgetError):
        budget.spend()


def test_retry_policy_attempts() -> None:
    assert RetryPolicy().attempts == 2
    assert RetryPolicy(retries=0).attempts == 1
    assert RetryPolicy(retries=2).attempts == 3
