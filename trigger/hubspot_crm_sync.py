"""HubSpot CRM sync Trigger.dev task (BJC-191).

Scheduled: 0 */6 * * * (every 6 hours)

Syncs HubSpot CRM data (contacts + deals + associations) to ClickHouse
for revenue attribution and analytics. Fan-out: all HubSpot-connected
tenants → per-tenant sync with error isolation.

Pattern: mirrors trigger/audience_refresh.py.
"""

import logging
import time
from datetime import UTC, datetime

from app.db.clickhouse import get_clickhouse_client
from app.db.supabase import get_supabase_client
from app.integrations.hubspot_engine_x import HubSpotEngineClient
from app.integrations.hubspot_syncer import HubSpotSyncer
from app.services.crm_clickhouse import insert_crm_contacts, insert_crm_opportunities

logger = logging.getLogger(__name__)


async def get_hubspot_connected_tenants(supabase) -> list[dict]:
    """Find all orgs with an active HubSpot CRM connection.

    Reads provider_configs where provider='hubspot_crm' and status='connected'.
    Returns list of {org_id, hubspot_client_id, last_hubspot_sync}.
    """
    res = (
        supabase.table("provider_configs")
        .select("organization_id, config")
        .eq("provider", "hubspot_crm")
        .execute()
    )

    tenants = []
    for row in res.data or []:
        config = row.get("config") or {}
        if config.get("status") != "connected":
            continue
        client_id = config.get("hubspot_client_id")
        if not client_id:
            continue
        tenants.append({
            "org_id": row["organization_id"],
            "hubspot_client_id": client_id,
            "last_hubspot_sync": config.get("last_hubspot_sync"),
        })

    return tenants


async def sync_tenant_hubspot(
    tenant: dict,
    syncer: HubSpotSyncer,
    supabase,
    clickhouse,
) -> dict:
    """Sync a single tenant's HubSpot CRM data to ClickHouse.

    Steps:
    1. Check connection health
    2. Pull contacts (incremental if last_hubspot_sync exists)
    3. Pull opportunities with associations
    4. Write to ClickHouse
    5. Update last_hubspot_sync in provider_configs
    """
    org_id = tenant["org_id"]
    client_id = tenant["hubspot_client_id"]
    last_sync = tenant.get("last_hubspot_sync")
    start_ms = time.monotonic_ns() // 1_000_000

    # 1. Check connection
    is_connected = await syncer.check_connection(client_id)
    if not is_connected:
        logger.warning(
            "HubSpot connection not active for tenant=%s client=%s — skipping",
            org_id, client_id,
        )
        return {
            "task": "hubspot_crm_sync",
            "tenant_id": org_id,
            "status": "skipped_disconnected",
        }

    # 2. Pull contacts
    contacts = await syncer.pull_contacts(client_id, since=last_sync)

    # 3. Pull opportunities with contact associations
    opportunities = await syncer.pull_opportunities(client_id, since=last_sync)

    # 4. Write to ClickHouse
    contacts_written = insert_crm_contacts(
        org_id, "hubspot", contacts, clickhouse=clickhouse,
    )
    opps_written = insert_crm_opportunities(
        org_id, "hubspot", opportunities, clickhouse=clickhouse,
    )

    # 5. Update last_sync_date
    now_iso = datetime.now(UTC).isoformat()
    supabase.rpc("update_provider_config_field", {
        "p_org_id": org_id,
        "p_provider": "hubspot_crm",
        "p_field": "last_hubspot_sync",
        "p_value": now_iso,
    }).execute()

    duration_ms = time.monotonic_ns() // 1_000_000 - start_ms
    return {
        "task": "hubspot_crm_sync",
        "tenant_id": org_id,
        "contacts_synced": contacts_written,
        "opportunities_synced": opps_written,
        "duration_ms": duration_ms,
        "status": "success",
    }


async def hubspot_crm_sync_task():
    """Scheduled HubSpot CRM sync — every 6 hours.

    Fan-out: all connected tenants → per-tenant sync.
    Per-tenant error isolation: one failure doesn't stop others.
    """
    supabase = get_supabase_client()
    clickhouse = get_clickhouse_client()

    tenants = await get_hubspot_connected_tenants(supabase)
    logger.info(
        "HubSpot CRM sync starting for %d tenants", len(tenants),
    )

    all_results = []
    async with HubSpotEngineClient() as hs_client:
        syncer = HubSpotSyncer(engine_client=hs_client)

        for tenant in tenants:
            try:
                result = await sync_tenant_hubspot(
                    tenant=tenant,
                    syncer=syncer,
                    supabase=supabase,
                    clickhouse=clickhouse,
                )
                all_results.append(result)
                logger.info(
                    "HubSpot sync complete for tenant=%s — %d contacts, %d opps",
                    tenant["org_id"],
                    result.get("contacts_synced", 0),
                    result.get("opportunities_synced", 0),
                )
            except Exception:
                logger.exception(
                    "HubSpot CRM sync failed for tenant %s", tenant["org_id"],
                )
                all_results.append({
                    "task": "hubspot_crm_sync",
                    "tenant_id": tenant["org_id"],
                    "status": "error",
                })

    total_contacts = sum(r.get("contacts_synced", 0) for r in all_results)
    total_opps = sum(r.get("opportunities_synced", 0) for r in all_results)
    logger.info(
        "HubSpot CRM sync finished: %d tenants, %d contacts, %d opps",
        len(tenants), total_contacts, total_opps,
    )
    return all_results
