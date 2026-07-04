"""Load the synthetic demo fixtures (Lane D owns the JSON) into the database.

Reads ``data/synthetic/patients.json`` and ``data/synthetic/results.json`` — arrays of objects that
validate against :class:`~cyclesentinel.schemas.Patient` and
:class:`~cyclesentinel.schemas.HormoneResult`. Both are optional: if a file is missing the seed is a
no-op for that table, so the app boots even before Lane D lands the corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from cyclesentinel.db.models import BriefRow, PatientRow, ResultRow, RunRow, StepRow
from cyclesentinel.schemas import HormoneResult, Patient

# apps/api/src/cyclesentinel/db/seed.py -> repo root is five parents up.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SYNTHETIC_DIR = _REPO_ROOT / "data" / "synthetic"


def _load_json_array(path: Path) -> list[dict[str, object]]:
    """Return the JSON array at ``path``, or ``[]`` if the file does not exist / is not a list."""
    if not path.is_file():
        return []
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def load_demo_patients(synthetic_dir: Path = _SYNTHETIC_DIR) -> list[Patient]:
    """Parse ``patients.json`` into validated :class:`Patient` models (empty if absent)."""
    items = _load_json_array(synthetic_dir / "patients.json")
    return [Patient.model_validate(item) for item in items]


def load_demo_results(synthetic_dir: Path = _SYNTHETIC_DIR) -> list[HormoneResult]:
    """Parse ``results.json`` into validated :class:`HormoneResult` models (empty if absent)."""
    return [
        HormoneResult.model_validate(item)
        for item in _load_json_array(synthetic_dir / "results.json")
    ]


def seed_demo(session: Session, synthetic_dir: Path = _SYNTHETIC_DIR) -> int:
    """Insert demo patients + results if the patients table is empty; return rows inserted.

    Idempotent: re-running when patients already exist is a no-op (use :func:`reset_demo` to force).
    """
    existing = session.get(PatientRow, _first_patient_id(synthetic_dir))
    if existing is not None:
        return 0

    inserted = 0
    for patient in load_demo_patients(synthetic_dir):
        session.merge(
            PatientRow(
                id=patient.id,
                label=patient.label,
                protocol=str(patient.protocol),
                cycle_day=patient.cycle_day,
                amh=patient.amh,
                antral_follicle_count=patient.antral_follicle_count,
                pcos_flag=patient.pcos_flag,
            )
        )
        inserted += 1
    for result in load_demo_results(synthetic_dir):
        session.merge(
            ResultRow(
                id=result.id,
                patient_id=result.patient_id,
                cycle_day=result.cycle_day,
                drawn_at=result.drawn_at,
                e2=result.e2,
                lh=result.lh,
                progesterone=result.progesterone,
                fsh=result.fsh,
                hcg=result.hcg,
                mature_follicle_count=result.mature_follicle_count,
            )
        )
        inserted += 1
    session.flush()
    return inserted


def reset_demo(session: Session, synthetic_dir: Path = _SYNTHETIC_DIR) -> int:
    """Wipe all runtime tables and reseed from the synthetic fixtures; return rows inserted."""
    session.execute(delete(StepRow))
    session.execute(delete(RunRow))
    session.execute(delete(BriefRow))
    session.execute(delete(ResultRow))
    session.execute(delete(PatientRow))
    session.flush()
    return seed_demo(session, synthetic_dir)


def _first_patient_id(synthetic_dir: Path) -> str:
    """Return the id of the first fixture patient (idempotency probe), or a sentinel."""
    patients = load_demo_patients(synthetic_dir)
    return patients[0].id if patients else "__no_demo_patients__"
