#!/usr/bin/env python3
"""Backfill WeChat nicknames for customers still showing external_userid."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db import get_session_factory, init_db  # noqa: E402
from app.models import Customer  # noqa: E402
from app.services.customer_display import (  # noqa: E402
    display_name_is_placeholder,
    enrich_customer_display_names,
)
from app.services.wecom_kf_client import WecomKfClient  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print how many customers would be refreshed",
    )
    args = parser.parse_args()

    init_db()
    factory = get_session_factory()
    db = factory()
    try:
        customers = db.query(Customer).all()
        pending = [c for c in customers if display_name_is_placeholder(c)]
        if args.dry_run:
            print(f"would refresh {len(pending)} / {len(customers)} customers")
            for customer in pending:
                print(f"  {customer.external_userid}")
            return 0

        with WecomKfClient() as client:
            enrich_customer_display_names(db, client, pending)
        db.commit()

        updated = sum(
            1
            for customer in pending
            if not display_name_is_placeholder(customer)
        )
        print(f"updated {updated} / {len(pending)} customers")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
