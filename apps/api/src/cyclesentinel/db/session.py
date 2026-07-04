"""Engine + session wiring.

SQLite by default (zero-infra for tests and ``make dev``); Postgres engages automatically when
``database_url`` points at ``postgresql``. Schema is created with ``Base.metadata.create_all`` —
adequate for the POC, so there is no Alembic migration story.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cyclesentinel.config import Settings, get_settings
from cyclesentinel.db.models import Base


def make_engine(url: str) -> Engine:
    """Build an :class:`~sqlalchemy.Engine` for ``url``.

    SQLite (file or in-memory) gets ``check_same_thread=False`` so a session can be shared across
    threads; in-memory SQLite additionally uses a :class:`StaticPool` so every connection sees the
    same database. Postgres and other backends use their default pooling.
    """
    if url.startswith("sqlite"):
        is_memory = ":memory:" in url or url.endswith(":memory:") or "mode=memory" in url
        if is_memory:
            return create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                future=True,
            )
        return create_engine(url, connect_args={"check_same_thread": False}, future=True)
    return create_engine(url, pool_pre_ping=True, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a :class:`sessionmaker` bound to ``engine`` and create the schema if needed."""
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session, future=True)


def _default_factory() -> sessionmaker[Session]:
    settings: Settings = get_settings()
    return make_session_factory(make_engine(settings.database_url))


# Process-wide session factory bound to the configured database URL.
SessionLocal: sessionmaker[Session] = _default_factory()


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a session that commits on success and rolls back on error, then closes."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
