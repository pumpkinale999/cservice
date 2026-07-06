"""WeCom customer nickname enrichment for display_name."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import Customer
from app.services.wecom_errors import CserviceWecomError
from app.services.wecom_kf_client import WecomKfClient

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


def display_name_is_placeholder(customer: Customer) -> bool:
    name = (customer.display_name or "").strip()
    return not name or name == customer.external_userid


def enrich_customer_display_names(
    db: Session,
    client: WecomKfClient,
    customers: list[Customer],
) -> None:
    """Fetch WeChat nicknames via kf/customer/batchget and update display_name."""
    pending = [c for c in customers if display_name_is_placeholder(c)]
    if not pending:
        return

    for start in range(0, len(pending), _BATCH_SIZE):
        chunk = pending[start : start + _BATCH_SIZE]
        external_userids = [c.external_userid for c in chunk]
        try:
            data = client.customer_batchget(external_userids)
        except CserviceWecomError as exc:
            logger.warning(
                "customer_batchget failed errcode=%s external_userids=%s",
                exc.errcode,
                external_userids,
            )
            continue

        by_id = {
            str(row.get("external_userid", "")): row
            for row in (data.get("customer_list") or [])
        }
        for customer in chunk:
            row = by_id.get(customer.external_userid)
            if not row:
                continue
            nickname = str(row.get("nickname") or "").strip()
            if nickname:
                customer.display_name = nickname
