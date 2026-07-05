"""Pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.db import reset_engine_cache


@pytest.fixture()
def tmp_cservice_db(tmp_path, monkeypatch):
    db_path = tmp_path / "cservice.db"
    monkeypatch.setenv("CSERVICE_DB_PATH", str(db_path))
    reset_engine_cache()
    repo_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    cfg.attributes["skip_log_config"] = True
    command.upgrade(cfg, "head")
    yield db_path
    reset_engine_cache()
