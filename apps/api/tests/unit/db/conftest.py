"""Fixtures for the persistence unit tests: a fresh in-memory SQLite session per test."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from cyclesentinel.db.session import make_engine, make_session_factory


@pytest.fixture
def session() -> Iterator[Session]:
    """Yield a session bound to a throwaway in-memory SQLite database with the schema created."""
    factory = make_session_factory(make_engine("sqlite+pysqlite:///:memory:"))
    db = factory()
    try:
        yield db
        db.commit()
    finally:
        db.close()
