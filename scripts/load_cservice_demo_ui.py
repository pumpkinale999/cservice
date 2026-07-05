#!/usr/bin/env python3
"""Load demo customers/sessions for UI smoke (non-production WeCom)."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db import get_session_factory, init_db  # noqa: E402
from app.models import Customer, Draft, Message, Session as CSession  # noqa: E402
from app.services.seed import load_seed_file  # noqa: E402

OPEN_KFID = "wkTEST_MINIMAL"
DEMO_CUSTOMERS = (
    ("wm_demo_001", "李女士", "想了解一下产品价格", 1),
    ("wm_demo_002", "王先生", "售后问题咨询", 0),
)


def _upsert_demo(db, *, servicer: str) -> int:
    created = 0
    for external_userid, display_name, preview, pending in DEMO_CUSTOMERS:
        existing = (
            db.query(CSession)
            .join(Customer, Customer.id == CSession.customer_id)
            .filter(
                CSession.servicer_userid == servicer,
                Customer.external_userid == external_userid,
            )
            .first()
        )
        if existing:
            continue
        cid = str(uuid.uuid4())
        sid = str(uuid.uuid4())
        now = "2026-07-05T14:00:00+00:00"
        db.add(
            Customer(
                id=cid,
                external_userid=external_userid,
                display_name=display_name,
                first_scene="官网",
                last_scene="官网",
                created_at=now,
            )
        )
        db.add(
            CSession(
                id=sid,
                open_kfid=OPEN_KFID,
                customer_id=cid,
                servicer_userid=servicer,
                status="open",
                pending_reply_count=pending,
                last_activity_at=now,
            )
        )
        db.add(
            Message(
                id=str(uuid.uuid4()),
                session_id=sid,
                direction="inbound",
                wx_msgid=f"wx_demo_{external_userid}",
                msg_type="text",
                content=preview,
                sender_type="customer",
                created_at=now,
            )
        )
        if pending:
            db.add(
                Draft(
                    id=str(uuid.uuid4()),
                    session_id=sid,
                    agent_text=f"您好，我是客服助理，关于「{preview}」我们可以为您详细介绍。",
                    status="pending",
                    created_at=now,
                )
            )
        created += 1
    db.commit()
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Load cservice demo UI data")
    parser.add_argument(
        "--servicers",
        default=os.environ.get("CSERVICE_DEMO_SERVICERS", "victor"),
        help="Comma-separated wecom_userid list (default: victor or CSERVICE_DEMO_SERVICERS)",
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=REPO_ROOT / "tests" / "fixtures" / "cservice" / "seed_minimal.yaml",
        help="Seed YAML (kf_accounts/servicers)",
    )
    args = parser.parse_args()
    servicers = [s.strip() for s in args.servicers.split(",") if s.strip()]
    if not servicers:
        print("error: no servicers", file=sys.stderr)
        return 1

    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        load_seed_file(args.seed.expanduser().resolve(), session)
        session.commit()
        total = 0
        for servicer in servicers:
            total += _upsert_demo(session, servicer=servicer)
    except Exception as exc:
        session.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()

    print(f"demo UI ready: servicers={servicers} new_sessions={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
