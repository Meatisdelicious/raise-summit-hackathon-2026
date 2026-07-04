"""Shared helpers and the ``thresholds.json`` shape used by the calculators.

The :class:`Thresholds` TypedDict documents exactly what
``data/synthetic/thresholds.json`` must contain (Lane D owns that file). The
calculators index into this shape, so a JSON blob loaded with ``json.load`` can
be passed straight through — the TypedDict keeps mypy ``--strict`` happy while
keeping the numbers out of the code (hard rule: thresholds are cited, never
hardcoded magic numbers).

Units (synthetic): E2 in pg/mL, progesterone in ng/mL, follicles as a count.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from cyclesentinel.schemas import HormoneResult


class OhssThresholds(TypedDict):
    """OHSS-composite thresholds (``rule_type = "ohss"``)."""

    e2_high: float  # absolute E2 level (pg/mL) that counts toward OHSS risk
    rate_pct_per_day_high: float  # steep E2 rate-of-rise (%/day)
    mature_follicle_count_high: int  # high mature-follicle count
    pcos_threshold_multiplier: float  # <1.0 lowers every OHSS threshold when PCOS


class ProgesteroneBand(TypedDict):
    """One cycle-day band of the progesterone threshold (first band whose
    ``max_cycle_day >= cycle_day`` wins)."""

    max_cycle_day: int
    threshold: float  # progesterone ceiling (ng/mL) for cycle days <= max_cycle_day


class LuteinizationThresholds(TypedDict):
    """Premature-luteinization thresholds (``rule_type = "luteinization"``)."""

    progesterone_by_cycle_day: list[ProgesteroneBand]
    default_threshold: float  # used when no band matches the cycle day


class PoorResponderThresholds(TypedDict):
    """Poor-responder thresholds (``rule_type = "poor_responder"``)."""

    flat_rate_pct_per_day: float  # avg E2 slope below this reads as "flat"
    min_e2_on_trajectory: float  # latest E2 below this reads as "still low"


class Thresholds(TypedDict):
    """The full ``thresholds.json`` shape passed to the calculators."""

    ohss: OhssThresholds
    luteinization: LuteinizationThresholds
    poor_responder: PoorResponderThresholds


def load_thresholds(path: str | Path) -> Thresholds:
    """Load ``data/synthetic/thresholds.json`` into the calculator :class:`Thresholds` TypedDict.

    The on-disk file mirrors this shape (plus optional ``citation`` provenance blocks, which are
    dropped here). Only the numeric fields the calculators index are extracted, so the returned
    payload trips the deterministic signals exactly per ``data/synthetic/manifest.json``.
    """
    raw: object = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"malformed thresholds (expected object): {path}")

    ohss = _require_block(raw, "ohss", path)
    lut = _require_block(raw, "luteinization", path)
    poor = _require_block(raw, "poor_responder", path)

    bands = lut["progesterone_by_cycle_day"]
    if not isinstance(bands, list):
        raise ValueError(
            f"thresholds luteinization.progesterone_by_cycle_day must be a list: {path}"
        )

    return Thresholds(
        ohss=OhssThresholds(
            e2_high=_as_float(ohss["e2_high"]),
            rate_pct_per_day_high=_as_float(ohss["rate_pct_per_day_high"]),
            mature_follicle_count_high=_as_int(ohss["mature_follicle_count_high"]),
            pcos_threshold_multiplier=_as_float(ohss["pcos_threshold_multiplier"]),
        ),
        luteinization=LuteinizationThresholds(
            progesterone_by_cycle_day=[
                ProgesteroneBand(
                    max_cycle_day=_as_int(band["max_cycle_day"]),
                    threshold=_as_float(band["threshold"]),
                )
                for band in bands
                if isinstance(band, dict)
            ],
            default_threshold=_as_float(lut["default_threshold"]),
        ),
        poor_responder=PoorResponderThresholds(
            flat_rate_pct_per_day=_as_float(poor["flat_rate_pct_per_day"]),
            min_e2_on_trajectory=_as_float(poor["min_e2_on_trajectory"]),
        ),
    )


def _require_block(raw: dict[str, object], key: str, path: str | Path) -> dict[str, object]:
    """Return ``raw[key]`` as a dict, raising a clear error if it is missing or malformed."""
    block = raw.get(key)
    if not isinstance(block, dict):
        raise ValueError(f"thresholds missing '{key}' object: {path}")
    return block


def _as_float(value: object) -> float:
    """Narrow a JSON-decoded number to ``float`` (mypy-strict safe)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raise ValueError(f"expected a number, got {value!r}")


def _as_int(value: object) -> int:
    """Narrow a JSON-decoded number to ``int`` (mypy-strict safe)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise ValueError(f"expected an integer, got {value!r}")


@dataclass(frozen=True)
class RateInfo:
    """The E2 rate-of-rise between the two most recent valid draws."""

    pct_per_day: float
    delta: float
    days: float
    prev_e2: float
    last_e2: float


def days_between(a: HormoneResult, b: HormoneResult) -> float:
    """Days from draw ``a`` to draw ``b`` (cycle-day delta, falling back to the
    wall-clock ``drawn_at`` delta when both land on the same cycle day)."""
    days = float(b.cycle_day - a.cycle_day)
    if days <= 0:
        days = (b.drawn_at - a.drawn_at).total_seconds() / 86400.0
    return days


def sorted_e2_points(results: Sequence[HormoneResult]) -> list[HormoneResult]:
    """Draws that carry an E2 value, oldest-first by cycle day then draw time."""
    pts = [r for r in results if r.e2 is not None]
    return sorted(pts, key=lambda r: (r.cycle_day, r.drawn_at))


def latest_e2_rate(results: Sequence[HormoneResult]) -> RateInfo | None:
    """E2 rate-of-rise between the last two valid draws, or ``None`` if there
    aren't two usable points."""
    pts = sorted_e2_points(results)
    if len(pts) < 2:
        return None
    prev, last = pts[-2], pts[-1]
    prev_e2, last_e2 = prev.e2, last.e2
    if prev_e2 is None or last_e2 is None or prev_e2 <= 0:
        return None
    days = days_between(prev, last)
    if days <= 0:
        return None
    delta = last_e2 - prev_e2
    pct_per_day = (delta / prev_e2 / days) * 100.0
    return RateInfo(
        pct_per_day=pct_per_day,
        delta=delta,
        days=days,
        prev_e2=prev_e2,
        last_e2=last_e2,
    )
