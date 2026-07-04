"""API test fixtures: an ASGI client over a seeded in-memory SQLite app in replay mode.

Env is set before importing the app so ``get_settings`` caches the in-memory database URL. Each
test gets a fresh app (fresh in-memory DB, re-seeded by the lifespan) with the scripted runner
wired in place of the (separately-owned) agent loop.
"""

from __future__ import annotations

import os

os.environ["CS_INFERENCE_MODE"] = "replay"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from collections.abc import AsyncIterator  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from cyclesentinel.config import get_settings  # noqa: E402
from cyclesentinel.main import create_app  # noqa: E402
from tests.api.scripted import scripted_factory  # noqa: E402


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Yield an ASGI client bound to a freshly started, seeded app with the scripted runner."""
    get_settings.cache_clear()
    app = create_app()
    async with app.router.lifespan_context(app):
        app.state.runner_factory = scripted_factory
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client
