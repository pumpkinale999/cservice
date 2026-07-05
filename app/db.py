"""SQLAlchemy engine and session."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


# Register ORM tables on Base.metadata for Alembic autogenerate.
from app.models import entities as _entities  # noqa: E402, F401


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        db_path = settings.cservice_db_path.expanduser().resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
        _engine = create_engine(url, connect_args={"check_same_thread": False})
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_session_factory():
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    get_engine()


def db_ok() -> bool:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def table_exists(name: str) -> bool:
    try:
        return inspect(get_engine()).has_table(name)
    except Exception:
        return False


def reset_engine_cache() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
