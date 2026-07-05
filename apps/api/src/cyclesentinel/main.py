"""FastAPI application entrypoint — ``cyclesentinel.main:app``.

The lifespan builds the engine + session factory (creating tables), seeds the synthetic demo state,
and wires the process singletons onto ``app.state``: the :class:`EventBus`, the runner factory, and
the background-task set. CORS is open for the frontend dev server.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cyclesentinel.api import api_router
from cyclesentinel.api.bus import EventBus
from cyclesentinel.api.deps import make_runner_factory
from cyclesentinel.config import get_settings
from cyclesentinel.db.seed import seed_demo
from cyclesentinel.db.session import make_engine, make_session_factory


def create_app() -> FastAPI:
    """Build a fully wired application instance (reads settings at call time)."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings.database_url)
        session_factory = make_session_factory(engine)
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.settings = settings
        app.state.bus = EventBus()
        app.state.runner_factory = make_runner_factory(settings)
        app.state.tasks = set[asyncio.Task[None]]()

        with session_factory() as session:
            seed_demo(session)
            session.commit()

        yield

        for task in list(app.state.tasks):
            task.cancel()
        engine.dispose()

    app = FastAPI(title="MILA API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
