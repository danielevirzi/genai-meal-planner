"""FastAPI application entrypoint for the backend API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.database import init_db
from api.routers import router


def _bool_env(var_name: str, default: bool) -> bool:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def create_app(seed_data: bool | None = None) -> FastAPI:
    seed_enabled = _bool_env("API_SEED_DATA", True) if seed_data is None else seed_data

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db(seed_data=seed_enabled)
        yield

    app = FastAPI(title="GenAI Meal Planner API", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
