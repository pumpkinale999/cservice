"""Round-robin assign."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import KfServicer
from app.services.assign import pick_servicer


def test_round_robin(loaded_seed):
    factory = get_session_factory()
    db = factory()
    try:
        db.add(
            KfServicer(
                open_kfid="wkTEST_MINIMAL",
                user_id="102",
                servicer_userid="lisi",
                sort_order=1,
            )
        )
        db.commit()
        first = pick_servicer(db, "wkTEST_MINIMAL")
        second = pick_servicer(db, "wkTEST_MINIMAL")
        assert {first, second} == {"zhangsan", "lisi"}
        assert first != second
    finally:
        db.close()
