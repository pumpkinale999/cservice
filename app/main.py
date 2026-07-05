"""FastAPI application entry (M1 scaffold)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routes_cservice import router as cservice_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="cservice", version="0.1.0-m1", lifespan=lifespan)
app.include_router(cservice_router, prefix=API_PREFIX)
