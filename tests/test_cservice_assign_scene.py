"""Scene route assign (CS-10)."""

from __future__ import annotations

from app.db import get_session_factory
from app.services.assign import pick_servicer


def test_scene_route_priority(loaded_seed):
    factory = get_session_factory()
    db = factory()
    try:
        picked = pick_servicer(db, "wkTEST_MINIMAL", scene="官网")
        assert picked == "lisi"
    finally:
        db.close()
