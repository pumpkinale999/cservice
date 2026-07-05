"""FastAPI application entry (M1 scaffold)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.hermes.ws_router import router as hermes_ws_router
from app.routes_cservice import router as cservice_router
from app.routes_internal import router as internal_router
from app.routes_kf_webhook import router as kf_webhook_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="cservice", version="0.4.0-m4", lifespan=lifespan)
app.include_router(cservice_router, prefix=API_PREFIX)
app.include_router(internal_router, prefix=API_PREFIX)
app.include_router(kf_webhook_router, prefix=API_PREFIX)
app.include_router(hermes_ws_router, prefix="/ws")
