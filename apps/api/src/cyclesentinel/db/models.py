"""SQLAlchemy 2.0 typed ORM rows for Cycle Sentinel.

Portable column types only (SQLite for local/CI, Postgres for the demo): ``String``/``Text`` for
UUID-text ids, ``JSON`` (not ``JSONB``) for list-valued columns such as ``states[]`` and
``citations[]``, and timezone-aware ``DateTime``. Rows are mapped to/from the Pydantic contract
models in :mod:`cyclesentinel.schemas` by :mod:`cyclesentinel.db.repo`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all Cycle Sentinel ORM rows."""


class PatientRow(Base):
    """A synthetic patient in IVF stimulation (mirrors :class:`~cyclesentinel.schemas.Patient`)."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(128))
    protocol: Mapped[str] = mapped_column(String(32))
    cycle_day: Mapped[int] = mapped_column(Integer)
    amh: Mapped[float] = mapped_column(Float)
    antral_follicle_count: Mapped[int] = mapped_column(Integer)
    pcos_flag: Mapped[bool] = mapped_column(Boolean)

    results: Mapped[list[ResultRow]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class ResultRow(Base):
    """A single serial hormone draw (mirrors :class:`~cyclesentinel.schemas.HormoneResult`)."""

    __tablename__ = "results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    cycle_day: Mapped[int] = mapped_column(Integer)
    drawn_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    e2: Mapped[float | None] = mapped_column(Float, nullable=True)
    lh: Mapped[float | None] = mapped_column(Float, nullable=True)
    progesterone: Mapped[float | None] = mapped_column(Float, nullable=True)
    fsh: Mapped[float | None] = mapped_column(Float, nullable=True)
    hcg: Mapped[float | None] = mapped_column(Float, nullable=True)
    mature_follicle_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    patient: Mapped[PatientRow] = relationship(back_populates="results")


class BriefRow(Base):
    """A cited monitoring brief (mirrors :class:`~cyclesentinel.schemas.MonitoringBrief`).

    ``states`` is a JSON array of :class:`~cyclesentinel.enums.DecisionState` string values;
    ``citations`` is a JSON array of citation objects (each ``{doc_id, rule_type, page, article,
    quote, score}``).
    """

    __tablename__ = "briefs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    result_id: Mapped[str] = mapped_column(ForeignKey("results.id"))
    run_id: Mapped[str] = mapped_column(String(64))
    states: Mapped[list[str]] = mapped_column(JSON, default=list)
    interpretation: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    escalation_level: Mapped[str] = mapped_column(String(16))
    validated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RunRow(Base):
    """An agent run (mirrors :class:`~cyclesentinel.schemas.RunSummary`)."""

    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    result_id: Mapped[str] = mapped_column(String(64))
    final_states: Mapped[list[str]] = mapped_column(JSON, default=list)
    brief_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    step_count: Mapped[int] = mapped_column(Integer, default=0)

    steps: Mapped[list[StepRow]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="StepRow.step"
    )


class StepRow(Base):
    """One ordered step of an agent run — powers the live trace + audit log."""

    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"))
    step: Mapped[int] = mapped_column(Integer)
    tool: Mapped[str] = mapped_column(String(64))
    args_summary: Mapped[str] = mapped_column(Text, default="")
    result_summary: Mapped[str] = mapped_column(Text, default="")
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    run: Mapped[RunRow] = relationship(back_populates="steps")
