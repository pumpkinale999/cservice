#!/usr/bin/env python3
"""Delete cservice sessions/customers except those matching --keep-display-name."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy.orm import Session  # noqa: E402

from app.db import get_session_factory, init_db  # noqa: E402
from app.models import (  # noqa: E402
    AgentThread,
    AssignRetry,
    Customer,
    Draft,
    Message,
    Session as CSession,
    UplinkRetry,
)


def _delete_session(db: Session, session_id: str) -> None:
    db.query(AssignRetry).filter_by(session_id=session_id).delete()
    db.query(UplinkRetry).filter_by(session_id=session_id).delete()
    db.query(Draft).filter_by(session_id=session_id).delete()
    db.query(Message).filter_by(session_id=session_id).delete()
    db.query(AgentThread).filter_by(session_id=session_id).delete()
    db.query(CSession).filter_by(id=session_id).delete()


def purge_by_display_names(db: Session, delete_names: set[str]) -> tuple[int, int]:
    rows = (
        db.query(CSession, Customer)
        .join(Customer, CSession.customer_id == Customer.id)
        .all()
    )
    deleted_sessions = 0
    deleted_customers = 0
    kept_customer_ids: set[str] = set()

    for csession, customer in rows:
        name = (customer.display_name or "").strip()
        if name not in delete_names:
            kept_customer_ids.add(customer.id)
            continue
        _delete_session(db, csession.id)
        deleted_sessions += 1

    for customer in db.query(Customer).all():
        if customer.id in kept_customer_ids:
            continue
        remaining = db.query(CSession).filter_by(customer_id=customer.id).count()
        if remaining == 0:
            db.delete(customer)
            deleted_customers += 1

    db.commit()
    return deleted_sessions, deleted_customers


def purge_except_display_names(db: Session, keep_names: set[str]) -> tuple[int, int]:
    rows = (
        db.query(CSession, Customer)
        .join(Customer, CSession.customer_id == Customer.id)
        .all()
    )
    deleted_sessions = 0
    deleted_customers = 0
    kept_customer_ids: set[str] = set()

    for csession, customer in rows:
        name = (customer.display_name or "").strip()
        if name in keep_names:
            kept_customer_ids.add(customer.id)
            continue
        _delete_session(db, csession.id)
        deleted_sessions += 1

    for customer in db.query(Customer).all():
        if customer.id in kept_customer_ids:
            continue
        remaining = (
            db.query(CSession).filter_by(customer_id=customer.id).count()
        )
        if remaining == 0:
            db.delete(customer)
            deleted_customers += 1

    db.commit()
    return deleted_sessions, deleted_customers


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge cservice sessions except kept names")
    parser.add_argument(
        "--keep-display-name",
        action="append",
        dest="keep_names",
        default=[],
        help="Customer display_name to keep (repeatable)",
    )
    parser.add_argument(
        "--delete-display-name",
        action="append",
        dest="delete_names",
        default=[],
        help="Customer display_name to delete (repeatable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List sessions that would be deleted without committing",
    )
    args = parser.parse_args()
    keep_names = {n.strip() for n in args.keep_names if n.strip()}
    delete_names = {n.strip() for n in args.delete_names if n.strip()}
    if not keep_names and not delete_names:
        print("error: specify --keep-display-name and/or --delete-display-name", file=sys.stderr)
        return 1
    if keep_names and delete_names:
        print("error: use either --keep-display-name or --delete-display-name, not both", file=sys.stderr)
        return 1

    init_db()
    factory = get_session_factory()
    db = factory()
    try:
        rows = (
            db.query(CSession, Customer)
            .join(Customer, CSession.customer_id == Customer.id)
            .all()
        )
        if delete_names:
            to_delete = [
                (csession.id, customer.display_name, customer.external_userid)
                for csession, customer in rows
                if (customer.display_name or "").strip() in delete_names
            ]
            to_keep = [
                (csession.id, customer.display_name, customer.external_userid)
                for csession, customer in rows
                if (customer.display_name or "").strip() not in delete_names
            ]
        else:
            to_delete = [
                (csession.id, customer.display_name, customer.external_userid)
                for csession, customer in rows
                if (customer.display_name or "").strip() not in keep_names
            ]
            to_keep = [
                (csession.id, customer.display_name, customer.external_userid)
                for csession, customer in rows
                if (customer.display_name or "").strip() in keep_names
            ]
        print(f"keep ({len(to_keep)}):")
        for sid, name, ext in to_keep:
            print(f"  {sid} name={name!r} ext={ext}")
        print(f"delete ({len(to_delete)}):")
        for sid, name, ext in to_delete:
            print(f"  {sid} name={name!r} ext={ext}")
        if args.dry_run:
            return 0
        if delete_names:
            deleted_sessions, deleted_customers = purge_by_display_names(db, delete_names)
        else:
            deleted_sessions, deleted_customers = purge_except_display_names(db, keep_names)
        print(f"done: deleted_sessions={deleted_sessions} deleted_customers={deleted_customers}")
    except Exception as exc:
        db.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
