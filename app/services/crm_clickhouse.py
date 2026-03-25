"""ClickHouse writer for CRM contact and opportunity data (BJC-190).

Accepts canonical CRMContact/CRMOpportunity models and inserts them into
the crm_contacts/crm_opportunities tables. Uses ReplacingMergeTree — duplicate
inserts for the same (tenant_id, crm_source, crm_*_id) are collapsed by synced_at.
"""

import logging
from datetime import UTC, datetime

from app.db.clickhouse import get_clickhouse_client
from app.integrations.crm_models import CRMContact, CRMOpportunity

logger = logging.getLogger(__name__)

# Column order must match the DDL (excluding synced_at which has a DEFAULT).

CONTACT_COLUMNS = [
    "tenant_id",
    "crm_source",
    "crm_contact_id",
    "email",
    "first_name",
    "last_name",
    "company_name",
    "account_id",
    "lead_source",
    "lifecycle_stage",
    "created_at",
    "updated_at",
]

OPPORTUNITY_COLUMNS = [
    "tenant_id",
    "crm_source",
    "crm_opportunity_id",
    "name",
    "amount",
    "close_date",
    "stage",
    "is_closed",
    "is_won",
    "account_id",
    "lead_source",
    "contact_ids",
    "created_at",
    "updated_at",
]

_EPOCH = datetime(1970, 1, 1)


def _dt_or_epoch(val: datetime | None) -> datetime:
    """ClickHouse DateTime64 doesn't accept None — use epoch as sentinel."""
    return val if val is not None else _EPOCH


def _contact_row(tenant_id: str, crm_source: str, c: CRMContact) -> list:
    return [
        tenant_id,
        crm_source,
        c.crm_contact_id,
        c.email,
        c.first_name,
        c.last_name,
        c.company_name,
        c.account_id,
        c.lead_source,
        c.lifecycle_stage,
        _dt_or_epoch(c.created_at),
        _dt_or_epoch(c.updated_at),
    ]


def _opportunity_row(tenant_id: str, crm_source: str, o: CRMOpportunity) -> list:
    return [
        tenant_id,
        crm_source,
        o.crm_opportunity_id,
        o.name,
        o.amount,
        o.close_date,
        o.stage,
        int(o.is_closed),
        int(o.is_won),
        o.account_id,
        o.lead_source,
        o.contact_ids,
        _dt_or_epoch(o.created_at),
        _dt_or_epoch(o.updated_at),
    ]


def insert_crm_contacts(
    tenant_id: str,
    crm_source: str,
    contacts: list[CRMContact],
    clickhouse=None,
) -> int:
    """Insert CRM contacts into ClickHouse. Returns rows inserted."""
    if not contacts:
        return 0
    ch = clickhouse or get_clickhouse_client()
    data = [_contact_row(tenant_id, crm_source, c) for c in contacts]
    ch.insert("crm_contacts", data, column_names=CONTACT_COLUMNS)
    logger.info(
        "Inserted %d crm_contacts for tenant=%s source=%s",
        len(data), tenant_id, crm_source,
    )
    return len(data)


def insert_crm_opportunities(
    tenant_id: str,
    crm_source: str,
    opportunities: list[CRMOpportunity],
    clickhouse=None,
) -> int:
    """Insert CRM opportunities into ClickHouse. Returns rows inserted."""
    if not opportunities:
        return 0
    ch = clickhouse or get_clickhouse_client()
    data = [_opportunity_row(tenant_id, crm_source, o) for o in opportunities]
    ch.insert("crm_opportunities", data, column_names=OPPORTUNITY_COLUMNS)
    logger.info(
        "Inserted %d crm_opportunities for tenant=%s source=%s",
        len(data), tenant_id, crm_source,
    )
    return len(data)


def get_last_sync_date(
    tenant_id: str,
    crm_source: str,
    clickhouse=None,
) -> datetime | None:
    """Get the most recent synced_at for a tenant+source from crm_contacts.

    Returns None if no records exist (initial sync).
    """
    ch = clickhouse or get_clickhouse_client()
    result = ch.query(
        "SELECT max(synced_at) FROM crm_contacts WHERE tenant_id = %(tid)s AND crm_source = %(src)s",
        parameters={"tid": tenant_id, "src": crm_source},
    )
    if result.result_rows and result.result_rows[0][0]:
        val = result.result_rows[0][0]
        if isinstance(val, datetime) and val > _EPOCH:
            return val
    return None
