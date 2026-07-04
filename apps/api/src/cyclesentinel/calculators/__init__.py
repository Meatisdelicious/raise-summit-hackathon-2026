"""Deterministic calculators (pure functions) that produce the computed signals.

Five are exposed as agent tools (``compute_e2_rate``, ``compute_e2_per_follicle``,
``compute_ohss_composite``, ``check_progesterone_for_day``,
``compute_next_draw_timing``); ``compute_response_curve`` runs in the compute
phase as a ComputedSignal that drives ``POOR_RESPONSE_FLAG``.

The ``Thresholds`` TypedDict documents the ``data/synthetic/thresholds.json`` shape.
"""

from __future__ import annotations

from cyclesentinel.calculators._util import (
    LuteinizationThresholds,
    OhssThresholds,
    PoorResponderThresholds,
    ProgesteroneBand,
    Thresholds,
    load_thresholds,
)
from cyclesentinel.calculators.e2_per_follicle import compute_e2_per_follicle
from cyclesentinel.calculators.e2_rate import compute_e2_rate
from cyclesentinel.calculators.next_draw_timing import compute_next_draw_timing
from cyclesentinel.calculators.ohss_composite import compute_ohss_composite
from cyclesentinel.calculators.progesterone_for_day import check_progesterone_for_day
from cyclesentinel.calculators.response_curve import compute_response_curve

__all__ = [
    "LuteinizationThresholds",
    "OhssThresholds",
    "PoorResponderThresholds",
    "ProgesteroneBand",
    "Thresholds",
    "check_progesterone_for_day",
    "compute_e2_per_follicle",
    "compute_e2_rate",
    "compute_next_draw_timing",
    "compute_ohss_composite",
    "compute_response_curve",
    "load_thresholds",
]
