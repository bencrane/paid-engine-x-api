"""Canonical CRM data models shared by HubSpot and Salesforce syncers (BJC-187).

These Pydantic models represent the normalized shape of CRM data.
All CRM integrations produce these types — ClickHouse writers consume them.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class CRMContact(BaseModel):
    """Canonical contact record from any CRM source."""

    crm_contact_id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    account_id: str | None = None
    lead_source: str | None = None
    lifecycle_stage: str | None = None
    lead_status: str | None = None
    job_title: str | None = None
    phone: str | None = None
    company_size: int | None = None
    industry: str | None = None
    linkedin_url: str | None = None
    owner_id: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CRMOpportunity(BaseModel):
    """Canonical opportunity/deal record from any CRM source."""

    crm_opportunity_id: str
    name: str
    amount: float | None = None
    close_date: date | None = None
    stage: str
    pipeline: str | None = None
    is_closed: bool = False
    is_won: bool = False
    account_id: str | None = None
    lead_source: str | None = None
    contact_ids: list[str] = Field(default_factory=list)
    owner_id: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PipelineStage(BaseModel):
    """CRM pipeline stage definition."""

    stage_id: str
    label: str
    display_order: int = 0
    is_closed: bool = False
    is_won: bool = False
    probability: float | None = None


class CRMSyncResult(BaseModel):
    """Result container for a full CRM sync pass."""

    tenant_id: str
    crm_source: str  # 'hubspot' or 'salesforce'
    contacts: list[CRMContact] = Field(default_factory=list)
    opportunities: list[CRMOpportunity] = Field(default_factory=list)
    pipeline_stages: list[PipelineStage] = Field(default_factory=list)


# --- HubSpot property parsing helpers ---


def parse_hs_float(value: Any) -> float | None:
    """Parse a HubSpot string property to float."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_hs_date(value: Any) -> date | None:
    """Parse a HubSpot date string (YYYY-MM-DD or epoch ms) to date."""
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    s = str(value)
    # HubSpot sometimes returns epoch milliseconds
    if s.isdigit() and len(s) >= 10:
        try:
            return datetime.fromtimestamp(int(s) / 1000).date()
        except (ValueError, OSError):
            pass
    # Standard date string
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_hs_datetime(value: Any) -> datetime | None:
    """Parse a HubSpot datetime string or epoch ms to datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    s = str(value)
    if s.isdigit() and len(s) >= 10:
        try:
            return datetime.fromtimestamp(int(s) / 1000)
        except (ValueError, OSError):
            pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def parse_hs_bool(value: Any) -> bool:
    """Parse a HubSpot boolean property (string 'true'/'false' or actual bool)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)
