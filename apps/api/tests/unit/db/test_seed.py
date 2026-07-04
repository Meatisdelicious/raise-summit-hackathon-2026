"""Tests for :mod:`cyclesentinel.db.seed` — fixture loading, idempotency, defensive absence."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from cyclesentinel.db import repo, seed

_PATIENTS = [
    {
        "id": "pat_k",
        "label": "Patient K",
        "protocol": "antagonist",
        "cycle_day": 8,
        "amh": 4.2,
        "antral_follicle_count": 24,
        "pcos_flag": True,
    },
    {
        "id": "pat_r",
        "label": "Patient R",
        "protocol": "long_agonist",
        "cycle_day": 7,
        "amh": 1.9,
        "antral_follicle_count": 11,
        "pcos_flag": False,
    },
]

_RESULTS = [
    {
        "id": "res_k1",
        "patient_id": "pat_k",
        "cycle_day": 8,
        "drawn_at": "2026-01-08T08:00:00Z",
        "e2": 3200.0,
        "lh": 3.1,
        "progesterone": 1.4,
        "fsh": None,
        "hcg": None,
        "mature_follicle_count": 18,
    }
]


def _write_fixtures(tmp_path: Path) -> Path:
    (tmp_path / "patients.json").write_text(json.dumps(_PATIENTS), encoding="utf-8")
    (tmp_path / "results.json").write_text(json.dumps(_RESULTS), encoding="utf-8")
    return tmp_path


def test_seed_demo_loads_fixtures(session: Session, tmp_path: Path) -> None:
    synthetic = _write_fixtures(tmp_path)
    inserted = seed.seed_demo(session, synthetic)
    assert inserted == 3  # 2 patients + 1 result
    assert {p.id for p in repo.list_patients(session)} == {"pat_k", "pat_r"}
    assert [r.id for r in repo.list_results(session, "pat_k")] == ["res_k1"]


def test_seed_demo_idempotent(session: Session, tmp_path: Path) -> None:
    synthetic = _write_fixtures(tmp_path)
    assert seed.seed_demo(session, synthetic) == 3
    assert seed.seed_demo(session, synthetic) == 0  # already seeded -> no-op


def test_seed_demo_missing_files_is_noop(session: Session, tmp_path: Path) -> None:
    # No JSON files written: defensive path, seeds nothing, does not raise.
    assert seed.seed_demo(session, tmp_path) == 0
    assert repo.list_patients(session) == []


def test_reset_demo_wipes_and_reseeds(session: Session, tmp_path: Path) -> None:
    synthetic = _write_fixtures(tmp_path)
    seed.seed_demo(session, synthetic)
    # Reset drops everything then reseeds from the same fixtures.
    assert seed.reset_demo(session, synthetic) == 3
    assert {p.id for p in repo.list_patients(session)} == {"pat_k", "pat_r"}
