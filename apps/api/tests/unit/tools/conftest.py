"""Fixtures for the tool unit tests: a seeded in-memory session + a wired ToolContext.

The ``thresholds`` fixture is the ``Thresholds`` TypedDict shape the calculators actually consume
(the calculators-lane reference payload), *not* the calculator-keyed ``thresholds.json`` on disk —
those two shapes differ, and the tool layer carries the TypedDict shape (see the lane handoff note).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from cyclesentinel.calculators import Thresholds
from cyclesentinel.db.models import PatientRow, ResultRow
from cyclesentinel.db.session import make_engine, make_session_factory
from cyclesentinel.inference.base import Clock, IdFactory
from cyclesentinel.inference.stub import StubRetriever
from cyclesentinel.tools import DoseRule, ToolContext, load_dose_rules

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SYNTHETIC = _REPO_ROOT / "data" / "synthetic"
_BASE = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)

PATIENT_ID = "pat_t"
RESULT_EARLY = "res_t1"
RESULT_LATEST = "res_t2"


@pytest.fixture
def session() -> Iterator[Session]:
    """A fresh in-memory SQLite session seeded with one PCOS patient and two serial draws."""
    factory = make_session_factory(make_engine("sqlite+pysqlite:///:memory:"))
    db = factory()
    db.add(
        PatientRow(
            id=PATIENT_ID,
            label="Patient T",
            protocol="antagonist",
            cycle_day=8,
            amh=4.2,
            antral_follicle_count=24,
            pcos_flag=True,
        )
    )
    db.add(
        ResultRow(
            id=RESULT_EARLY,
            patient_id=PATIENT_ID,
            cycle_day=6,
            drawn_at=_BASE + timedelta(days=6),
            e2=1200.0,
            lh=3.0,
            progesterone=0.8,
            fsh=None,
            hcg=None,
            mature_follicle_count=12,
        )
    )
    db.add(
        ResultRow(
            id=RESULT_LATEST,
            patient_id=PATIENT_ID,
            cycle_day=8,
            drawn_at=_BASE + timedelta(days=8),
            e2=3200.0,
            lh=3.1,
            progesterone=1.6,
            fsh=None,
            hcg=None,
            mature_follicle_count=18,
        )
    )
    db.flush()
    try:
        yield db
        db.commit()
    finally:
        db.close()


@pytest.fixture
def thresholds() -> Thresholds:
    """The ``Thresholds`` TypedDict payload the calculators consume."""
    return {
        "ohss": {
            "e2_high": 3500.0,
            "rate_pct_per_day_high": 50.0,
            "mature_follicle_count_high": 18,
            "pcos_threshold_multiplier": 0.85,
        },
        "luteinization": {
            "progesterone_by_cycle_day": [
                {"max_cycle_day": 8, "threshold": 1.5},
                {"max_cycle_day": 12, "threshold": 1.75},
            ],
            "default_threshold": 2.0,
        },
        "poor_responder": {
            "flat_rate_pct_per_day": 20.0,
            "min_e2_on_trajectory": 500.0,
        },
    }


@pytest.fixture
def dose_table() -> dict[str, DoseRule]:
    """The real ``dose_tables.json`` parsed into the ``{situation: DoseRule}`` map."""
    return load_dose_rules(_SYNTHETIC / "dose_tables.json")


@pytest.fixture
def ctx(session: Session, thresholds: Thresholds, dose_table: dict[str, DoseRule]) -> ToolContext:
    """A ToolContext wired to the seeded session, a stub retriever, and deterministic id/clock."""
    return ToolContext(
        session=session,
        retriever=StubRetriever(),
        thresholds=thresholds,
        dose_table=dose_table,
        corpus=None,
        ids=IdFactory("id"),
        clock=Clock(_BASE),
    )
