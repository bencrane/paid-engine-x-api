-- BJC-190: CRM contact and opportunity tables for HubSpot/Salesforce sync.
-- ReplacingMergeTree deduplicates on (tenant_id, crm_source, crm_*_id) using synced_at.

CREATE TABLE IF NOT EXISTS paid_engine_x_api.crm_contacts (
    tenant_id       String,
    crm_source      String,           -- 'salesforce' or 'hubspot'
    crm_contact_id  String,           -- SFDC Contact.Id or HubSpot hs_object_id
    email           String,
    first_name      Nullable(String),
    last_name       Nullable(String),
    company_name    Nullable(String),
    account_id      Nullable(String), -- SFDC AccountId or HubSpot company ID
    lead_source     Nullable(String),
    lifecycle_stage Nullable(String),
    created_at      DateTime64(3),
    updated_at      DateTime64(3),
    synced_at       DateTime64(3) DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(synced_at)
ORDER BY (tenant_id, crm_source, crm_contact_id);

CREATE TABLE IF NOT EXISTS paid_engine_x_api.crm_opportunities (
    tenant_id           String,
    crm_source          String,
    crm_opportunity_id  String,
    name                String,
    amount              Nullable(Float64),
    close_date          Nullable(Date),
    stage               String,
    is_closed           UInt8,
    is_won              UInt8,
    account_id          Nullable(String),
    lead_source         Nullable(String),
    contact_ids         Array(String),
    created_at          DateTime64(3),
    updated_at          DateTime64(3),
    synced_at           DateTime64(3) DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(synced_at)
ORDER BY (tenant_id, crm_source, crm_opportunity_id);
