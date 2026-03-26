"""Supabase writer for CRM contact and opportunity data.

Primary operational store for CRM entities. Upserts on
(organization_id, crm_source, external_id) — new records insert,
existing records update in place.
"""

import logging
from datetime import UTC, datetime

from app.db.supabase import get_supabase_client
from app.integrations.crm_models import CRMContact, CRMOpportunity

logger = logging.getLogger(__name__)


def _contact_row(org_id: str, crm_source: str, c: CRMContact) -> dict:
    """Map CRMContact to Supabase crm_contacts row."""
    return {
        "organization_id": org_id,
        "crm_source": crm_source,
        "external_id": c.crm_contact_id,
        "email": c.email or None,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "company_name": c.company_name,
        "job_title": c.job_title,
        "lifecycle_stage": c.lifecycle_stage,
        "lead_status": c.lead_status,
        "lead_source": c.lead_source,
        "owner_id": c.owner_id,
        "phone": c.phone,
        "company_size": c.company_size,
        "industry": c.industry,
        "linkedin_url": c.linkedin_url,
        "utm_source": c.utm_source,
        "utm_medium": c.utm_medium,
        "utm_campaign": c.utm_campaign,
        "utm_term": c.utm_term,
        "utm_content": c.utm_content,
        "crm_created_at": c.created_at.isoformat() if c.created_at else None,
        "crm_updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "synced_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _opportunity_row(org_id: str, crm_source: str, o: CRMOpportunity) -> dict:
    """Map CRMOpportunity to Supabase crm_opportunities row."""
    return {
        "organization_id": org_id,
        "crm_source": crm_source,
        "external_id": o.crm_opportunity_id,
        "name": o.name or None,
        "amount": float(o.amount) if o.amount is not None else None,
        "close_date": o.close_date.isoformat() if o.close_date else None,
        "stage": o.stage or None,
        "pipeline": o.pipeline,
        "is_closed": o.is_closed,
        "is_won": o.is_won,
        "account_id": o.account_id,
        "lead_source": o.lead_source,
        "contact_ids": o.contact_ids,
        "owner_id": o.owner_id,
        "utm_source": o.utm_source,
        "utm_medium": o.utm_medium,
        "utm_campaign": o.utm_campaign,
        "utm_term": o.utm_term,
        "utm_content": o.utm_content,
        "crm_created_at": o.created_at.isoformat() if o.created_at else None,
        "crm_updated_at": o.updated_at.isoformat() if o.updated_at else None,
        "synced_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def upsert_crm_contacts(
    contacts: list[CRMContact],
    org_id: str,
    crm_source: str,
    supabase=None,
) -> int:
    """Upsert CRM contacts into Supabase. Returns rows upserted."""
    if not contacts:
        return 0
    sb = supabase or get_supabase_client()
    rows = [_contact_row(org_id, crm_source, c) for c in contacts]
    sb.table("crm_contacts").upsert(
        rows,
        on_conflict="organization_id,crm_source,external_id",
    ).execute()
    logger.info(
        "Upserted %d crm_contacts to Supabase for org=%s source=%s",
        len(rows), org_id, crm_source,
    )
    return len(rows)


def upsert_crm_opportunities(
    opportunities: list[CRMOpportunity],
    org_id: str,
    crm_source: str,
    supabase=None,
) -> int:
    """Upsert CRM opportunities into Supabase. Returns rows upserted."""
    if not opportunities:
        return 0
    sb = supabase or get_supabase_client()
    rows = [_opportunity_row(org_id, crm_source, o) for o in opportunities]
    sb.table("crm_opportunities").upsert(
        rows,
        on_conflict="organization_id,crm_source,external_id",
    ).execute()
    logger.info(
        "Upserted %d crm_opportunities to Supabase for org=%s source=%s",
        len(rows), org_id, crm_source,
    )
    return len(rows)
