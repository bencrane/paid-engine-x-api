"""HubSpot CRM syncer — implements BaseCRMSyncer via HubSpotEngineClient (BJC-188).

Normalizes HubSpot's string-typed properties into canonical CRMContact/CRMOpportunity
models. Handles auto-pagination and association traversal.
"""

import logging
from typing import Any

from app.integrations.crm_base import BaseCRMSyncer
from app.integrations.crm_models import (
    CRMContact,
    CRMOpportunity,
    PipelineStage,
    parse_hs_bool,
    parse_hs_date,
    parse_hs_datetime,
    parse_hs_float,
)
from app.integrations.hubspot_engine_x import HubSpotEngineClient

logger = logging.getLogger(__name__)

# HubSpot properties to request for each object type.
CONTACT_PROPERTIES = [
    "email", "firstname", "lastname", "company", "associatedcompanyid",
    "hs_lead_status", "lifecyclestage", "createdate", "lastmodifieddate",
]

DEAL_PROPERTIES = [
    "dealname", "amount", "closedate", "dealstage", "pipeline",
    "hs_is_closed", "hs_is_closed_won", "hs_object_id",
    "associatedcompanyid", "hs_lead_source",
    "createdate", "hs_lastmodifieddate",
]


def _props(record: dict[str, Any]) -> dict[str, Any]:
    """Extract the properties dict from a HubSpot record."""
    return record.get("properties", {})


def _hs_id(record: dict[str, Any]) -> str:
    """Get the HubSpot object ID from a record."""
    return str(record.get("id", _props(record).get("hs_object_id", "")))


class HubSpotSyncer(BaseCRMSyncer):
    """CRM syncer that pulls data from HubSpot via hubspot-engine-x."""

    def __init__(self, engine_client: HubSpotEngineClient):
        self._client = engine_client

    def _normalize_contact(self, record: dict[str, Any]) -> CRMContact:
        """Convert a HubSpot contact record to canonical CRMContact."""
        p = _props(record)
        return CRMContact(
            crm_contact_id=_hs_id(record),
            email=p.get("email", ""),
            first_name=p.get("firstname"),
            last_name=p.get("lastname"),
            company_name=p.get("company"),
            account_id=p.get("associatedcompanyid"),
            lead_source=p.get("hs_lead_status"),
            lifecycle_stage=p.get("lifecyclestage"),
            created_at=parse_hs_datetime(p.get("createdate")),
            updated_at=parse_hs_datetime(p.get("lastmodifieddate")),
        )

    def _normalize_opportunity(
        self,
        record: dict[str, Any],
        contact_ids: list[str] | None = None,
    ) -> CRMOpportunity:
        """Convert a HubSpot deal record to canonical CRMOpportunity."""
        p = _props(record)
        return CRMOpportunity(
            crm_opportunity_id=_hs_id(record),
            name=p.get("dealname", ""),
            amount=parse_hs_float(p.get("amount")),
            close_date=parse_hs_date(p.get("closedate")),
            stage=p.get("dealstage", ""),
            is_closed=parse_hs_bool(p.get("hs_is_closed")),
            is_won=parse_hs_bool(p.get("hs_is_closed_won")),
            account_id=p.get("associatedcompanyid"),
            lead_source=p.get("hs_lead_source"),
            contact_ids=contact_ids or [],
            created_at=parse_hs_datetime(p.get("createdate")),
            updated_at=parse_hs_datetime(p.get("hs_lastmodifieddate")),
        )

    def _normalize_pipeline_stage(
        self,
        stage: dict[str, Any],
        display_order: int,
    ) -> PipelineStage:
        """Convert a HubSpot pipeline stage to canonical PipelineStage."""
        return PipelineStage(
            stage_id=stage.get("stageId", stage.get("id", "")),
            label=stage.get("label", ""),
            display_order=display_order,
            is_closed=parse_hs_bool(stage.get("isClosed")),
            is_won=parse_hs_bool(stage.get("isWon")),
            probability=parse_hs_float(stage.get("probability")),
        )

    # --- BaseCRMSyncer implementation ---

    async def pull_contacts(
        self,
        client_id: str,
        since: str | None = None,
    ) -> list[CRMContact]:
        """Pull contacts modified since timestamp, auto-paginating."""
        filters = []
        if since:
            filters.append({
                "propertyName": "lastmodifieddate",
                "operator": "GTE",
                "value": since,
            })

        records = await self._client.search_all(
            client_id=client_id,
            object_type="contacts",
            filters=filters,
            properties=CONTACT_PROPERTIES,
        )

        contacts = [self._normalize_contact(r) for r in records]
        logger.info(
            "Pulled %d contacts for client=%s (since=%s)",
            len(contacts), client_id, since,
        )
        return contacts

    async def pull_opportunities(
        self,
        client_id: str,
        since: str | None = None,
    ) -> list[CRMOpportunity]:
        """Pull deals modified since timestamp with contact associations."""
        filters = []
        if since:
            filters.append({
                "propertyName": "hs_lastmodifieddate",
                "operator": "GTE",
                "value": since,
            })

        records = await self._client.search_all(
            client_id=client_id,
            object_type="deals",
            filters=filters,
            properties=DEAL_PROPERTIES,
        )

        if not records:
            return []

        # Batch-read deal→contact associations
        deal_ids = [_hs_id(r) for r in records]
        assoc_map = await self._client.batch_associations(
            client_id=client_id,
            from_type="deals",
            to_type="contacts",
            record_ids=deal_ids,
        )

        opportunities = []
        for record in records:
            deal_id = _hs_id(record)
            contact_assocs = assoc_map.get(deal_id, [])
            contact_ids = [str(a.get("id", "")) for a in contact_assocs if a.get("id")]
            opportunities.append(
                self._normalize_opportunity(record, contact_ids=contact_ids)
            )

        logger.info(
            "Pulled %d opportunities for client=%s (since=%s)",
            len(opportunities), client_id, since,
        )
        return opportunities

    async def pull_pipeline_stages(
        self,
        client_id: str,
    ) -> list[PipelineStage]:
        """Pull all deal pipeline stages."""
        pipelines = await self._client.get_pipelines(
            client_id=client_id,
            object_type="deals",
        )

        stages: list[PipelineStage] = []
        for pipeline in pipelines:
            for i, stage_data in enumerate(pipeline.get("stages", [])):
                stages.append(self._normalize_pipeline_stage(stage_data, i))

        logger.info("Pulled %d pipeline stages for client=%s", len(stages), client_id)
        return stages

    async def push_lead(
        self,
        client_id: str,
        lead: dict,
        attribution: dict | None = None,
    ) -> str:
        """Push a lead as a HubSpot contact. Returns created record ID."""
        properties = {
            "email": lead.get("email", ""),
            "firstname": lead.get("first_name", ""),
            "lastname": lead.get("last_name", ""),
            "company": lead.get("company_name", ""),
        }
        if attribution:
            properties["hs_lead_source"] = attribution.get("source", "PaidEdge")

        results = await self._client.push_records(
            client_id=client_id,
            object_type="contacts",
            records=[{"properties": properties}],
        )
        if results:
            return str(results[0].get("id", ""))
        return ""

    async def check_connection(
        self,
        client_id: str,
    ) -> bool:
        """Check if HubSpot connection is active."""
        try:
            data = await self._client.get_connection(client_id)
            return data.get("status") == "connected"
        except Exception:
            logger.warning("Connection check failed for client=%s", client_id)
            return False
