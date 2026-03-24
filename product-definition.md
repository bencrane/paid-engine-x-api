# PaidEdge — Product Requirements Document

**Version:** 1.0  
**Date:** March 24, 2026  
**Author:** Benjamin, Outbound Solutions  
**Status:** North Star Vision — to be decomposed into Linear milestones/epics/tasks  
**Confidential**

---

## 1. Product Overview

### 1.1 One-Liner

PaidEdge is a multi-tenant B2B paid advertising platform that unifies audience building, campaign asset generation, campaign launch, cross-platform performance analytics, and CRM revenue attribution into a single product for heads of demand generation.

### 1.2 Core Thesis

B2B demand gen leaders currently stitch together 5–10 tools to run paid advertising. PaidEdge replaces that patchwork with a closed loop: discover targetable audiences via real signals → generate campaign-specific assets with AI → launch campaigns to ad platforms → track performance across platforms → tie results back to CRM pipeline and closed-won revenue. The entire loop lives in one product.

### 1.3 Target Users

**Primary:** Head of Demand Generation at a B2B technology company (Series A–C, $5–50M ARR). Their job is to test paid growth strategies, find what works, scale what works, and prove ROI to leadership.

**Secondary:** Paid media agencies running B2B campaigns for multiple clients. Multi-tenant architecture supports this natively — each client is an organization/tenant.

---

## 2. Problem Statement

No B2B demand gen leader has all of the following capabilities unified in one platform today:

1. **Audience discovery and segment building** — currently done across Clay, Apollo, ZoomInfo, LinkedIn Sales Nav, manual research. Fragmented, expensive, and non-composable.
2. **Campaign asset creation** — lead magnets, landing pages, ad creative currently require Canva, freelancers, internal design teams, or dedicated content tools. Slow and disconnected from targeting.
3. **Campaign launch and platform distribution** — currently done in native ad platform UIs (LinkedIn Campaign Manager, Meta Ads Manager, Google Ads), one platform at a time, no unified view.
4. **Cross-platform performance tracking** — currently done via spreadsheets, Whatagraph, Triple Whale, or HockeyStack. Siloed by platform, no unified campaign view.
5. **Revenue attribution tied to CRM pipeline** — currently requires manual Salesforce reports, HockeyStack ($28K/yr median), or Bizible. Most teams can't answer "which campaign generated how much closed-won revenue."

**Result:** Fragmented data, slow execution, no unified view, inability to answer "what's actually working and why," and massive time waste context-switching between tools.

---

## 3. Product Architecture — Core Loop

The product delivers a closed loop with five stages. Each stage feeds the next.

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  1. AUDIENCE     │────▶│  2. ASSET         │────▶│  3. CAMPAIGN   │
│  BUILDING        │     │  GENERATION       │     │  LAUNCH        │
│  (Signal Cards)  │     │  (AI-generated)   │     │  (Multi-plat)  │
└─────────────────┘     └──────────────────┘     └────────┬───────┘
        ▲                                                  │
        │                                                  ▼
┌─────────────────┐                              ┌────────────────┐
│  5. REVENUE      │◀────────────────────────────│  4. PERFORMANCE│
│  ATTRIBUTION     │                              │  ANALYTICS     │
│  (CRM join)      │                              │  (ClickHouse)  │
└─────────────────┘                              └────────────────┘
```

### 3.1 Audience Building — Signal Cards

**What the user sees:** On login, a dashboard of actionable audience signal cards. Each card represents a targetable segment with a count, description, and "Activate" action. These are not static lists — they are dynamic, refreshed segments surfaced by PaidEdge based on real data from multiple sources.

**Example signal cards:**

- "127 CISOs at companies searching for SOC 2 compliance" *(coming later — TrustRadius)*
- "34 VPs of Engineering who are new in their role (last 30 days)"
- "18 companies that just raised Series B ($10M+)"
- "52 people who liked/commented on your last 5 LinkedIn posts"
- "7 companies visiting your pricing page this week"
- "23 people who downloaded your SOC 2 compliance guide but didn't book a demo"
- "Lookalike segment: 200 companies that match your top 10 closed-won accounts"

**V1 Signal Sources — In Product (available at launch):**

| Signal | Data Source | Mechanism | Cost to PaidEdge |
|--------|-----------|-----------|-----------------|
| New in role | BlitzAPI | Job title change detection against stored snapshots. Trigger.dev runs daily/weekly delta comparisons against previously stored person records. | Near-zero (BlitzAPI unlimited) |
| Senior exec departed | BlitzAPI | Same delta detection — person record at company disappears or title changes to different company. | Near-zero |
| Promoted | BlitzAPI | Title seniority upgrade detected in delta. | Near-zero |
| Company raised money | BlitzAPI or public data | Funding event data from BlitzAPI company enrichment or ingested from public sources (Crunchbase-style). | Near-zero |
| Lookalikes of closed-won | BlitzAPI + CRM | Pull closed-won accounts from CRM (Salesforce/HubSpot via RudderStack), extract firmographic profile, query BlitzAPI for matching companies. | Near-zero |
| Closed-lost exclusions | CRM | Pull closed-lost accounts from CRM, build exclusion segment. | Zero |
| LinkedIn post engagers | Trigify API or Clay | Extract all likers/commenters from client's LinkedIn posts. Trigify: PAYG at $0.012/credit with open API. Clay: 1 action per post extraction. | Low — ~$0.012/engager via Trigify or 1 Clay action per post |
| Companies visiting key pages | Clay web intent + RudderStack | RudderStack JS SDK tracks page visits. When a visitor hits a designated high-intent page (pricing, case studies, demo), fire Clay web intent lookup to resolve company via IP waterfall (Snitcher, Warmly, Demandbase, Clearbit, Dealfront, PDL, Versium). ~2–4 Clay credits per successful resolution. | Low — ~4 credits × $0.05 = $0.20/resolution. Typical B2B site: a few hundred pricing page visitors/mo = ~$40–100/mo. Absorbed by PaidEdge. |
| Lead magnet downloaders | Self-identified (form fill) | Person submitted a form on a PaidEdge-generated landing page. Identity is known. Stored in Supabase + ClickHouse. | Zero |
| Custom segments via chat | Claude API + BlitzAPI/enrichment | User types natural language query ("show me all DevOps managers at companies with 200–500 employees in fintech"). PaidEdge translates to enrichment queries. | Near-zero |
| Deep research signals | Parallel.ai, OpenClaw, NemoClaw | "Companies that have X on their site," "companies that announced Y," etc. AI web research agents find qualifying companies. | TBD — depends on provider pricing and volume |

**Coming Later (post-V1):**

| Signal | Data Source | Mechanism | Blocker |
|--------|-----------|-----------|---------|
| "Companies searching for [category]" | TrustRadius (direct API) | High-fidelity second-party intent — companies actively reading reviews/comparing products in a specific category on TrustRadius.com. | Data cost. TrustRadius via Clay = 10 credits/result (~$0.50/result), prohibitively expensive at scale. Direct TrustRadius API deal requires annual contract PaidEdge can't fund yet. Will pursue when revenue justifies. |
| Bombora topic surge | Bombora or via Propensity | Third-party intent — companies consuming abnormally high content on specific topics across 5,000+ B2B publisher co-op. | Requires Bombora direct deal or Propensity API ($2K+/mo). Not viable for V1. |

**Technical implementation — Audience Engine:**

- **Storage:** Audience segment definitions stored in Supabase (`audience_segments` table). Each segment has: tenant_id, segment_type (enum: new_in_role, raised_money, page_visitor, etc.), filter_config (JSONB — the parameters), refresh_schedule, last_refreshed_at, member_count.
- **Member resolution:** Segment members are materialized into ClickHouse (`audience_segment_members` table) on refresh. Each row: segment_id, person_id or company_id, matched_at, signal_strength score.
- **Refresh orchestration:** Trigger.dev scheduled tasks per segment type. Delta-based where possible (BlitzAPI snapshots). Event-driven for real-time signals (page visits via RudderStack webhook → Clay → ClickHouse).
- **Chat-driven builder:** Claude API call with system prompt containing available signal types, enrichment capabilities, and current tenant's data schema. Returns a structured segment definition that PaidEdge validates and executes.

### 3.2 Campaign Asset Generation

**Core principle:** Assets are generated per-campaign, not pre-created and stored globally. The marginal cost of AI-generated content is effectively zero, so every campaign should have bespoke assets tailored to the specific audience segment and angle.

**Asset types:**

| Asset Type | Generation Method | Output Format | Hosting |
|-----------|------------------|--------------|---------|
| Lead magnets | Claude API with client context (customer stories, brand guidelines, testimonials) | PDF (generated via code) | PaidEdge-hosted, gated behind form |
| Landing pages | Claude API generates HTML/React page | HTML | PaidEdge-hosted subdomain or client subdomain (TBD) |
| Ad creative — copy | Claude API with campaign angle + audience context | Text (headline, body, CTA per platform) | Delivered to ad platform via API or copy/paste |
| Ad creative — image concepts | Claude API generates briefs/concepts | Text brief + potential AI image generation | TBD — may integrate image gen or output briefs for designer |
| Motion graphic video | TBD | Video | Future — not V1 |
| Email nurture copy | Claude API | Text (subject, body, CTA) | Delivered to email tool or built-in send |

**Client onboarding inputs (persistent, reusable across campaigns):**

These are NOT global assets. They are raw material inputs the AI draws from when generating campaign-specific assets:

- Customer list with logos and ARR/deal size
- Recorded testimonials (audio/video — transcribed and stored)
- Case study narratives (text or transcribed from recordings)
- Brand guidelines (colors, voice, tone rules)
- Product positioning docs
- Competitor differentiators
- ICP definition

Stored in Supabase per-tenant: `tenant_context` table with context_type enum and content (text/URL to stored file).

### 3.3 Campaign Launch

**What the user does:** Selects an audience segment → reviews AI-generated assets → picks target platforms (LinkedIn, Meta, Google Ads) → sets budget and schedule → launches.

**Audience push to ad platforms — V1 approach:**

The most difficult part of this stage is getting audience lists into the ad platforms. Options and sequencing:

1. **Clay Ads integration (if on Clay modern plan):** Clay's LinkedIn/Meta/Google Ads write integration pushes audience lists and keeps them synced. This requires Clay Growth plan ($495+/mo) which PaidEdge may or may not be on. If available, this is the fastest path.
2. **Direct API integrations (build over time):**
   - **LinkedIn Marketing API** — Customer Audiences endpoint for matched audiences (requires LinkedIn partner approval and customer OAuth)
   - **Meta Custom Audiences API** — upload hashed email lists
   - **Google Ads Customer Match API** — upload hashed email lists
3. **CSV export + manual upload** — fallback for V1 if neither of the above is ready. PaidEdge generates a platform-formatted CSV, user uploads manually.

**Email resolution for audience push:** Ad platforms match on email (hashed). BlitzAPI provides company/person enrichment but NOT personal email. For email resolution: use Prospeo API (`company_website` preferred over `company_name` for Enrich Person endpoint) or Clay credits for email finding. Match rates will be "good enough" — running Meta/LinkedIn ads is a secondary citizen compared to the audience building and analytics value.

**Sendoso integration:** Optional. For campaigns with incentive-attached offers (e.g., "book a meeting, get a $50 gift card"). Sendoso API triggered when a campaign includes an incentive configuration.

**Campaign data model:**

```
campaigns
├── id (uuid)
├── tenant_id (uuid, FK → organizations)
├── name (text)
├── status (enum: draft, active, paused, completed)
├── audience_segment_id (uuid, FK → audience_segments)
├── platforms (jsonb — array of {platform: 'linkedin'|'meta'|'google', platform_campaign_id: text, budget: numeric, ...})
├── assets (jsonb — references to generated assets)
├── incentive_config (jsonb, nullable — Sendoso params)
├── created_at, updated_at
├── launched_at (timestamp, nullable)
└── completed_at (timestamp, nullable)
```

### 3.4 Performance Analytics

**Data flow:** Ad platform APIs (LinkedIn, Meta, Google Ads) → RudderStack Cloud Sources → ClickHouse.

**What gets pulled:**

- Campaign-level: spend, impressions, clicks, CTR, CPC, CPM, conversions, ROAS
- Ad group / ad set level: same metrics broken down
- Ad-level: individual ad performance
- Time series: daily granularity minimum

**Dashboard views:**

1. **Campaign overview** — all active campaigns across all platforms, sortable by any metric. KPI cards at top (total spend, average CAC, total conversions, pipeline influenced).
2. **Single campaign detail** — deep dive into one campaign. Platform breakdown (if cross-platform). Budget pacing vs. target with progress bars. Time series charts (spend, conversions, CPC over time).
3. **Cross-platform comparison** — same audience segment targeted on LinkedIn vs. Meta vs. Google. Side-by-side performance. Which platform is winning?
4. **AI recommendations** — generated by Claude API analyzing campaign data in ClickHouse. Output: actionable cards like "Increase Meta retargeting budget +15% — projected to add 8 pipeline opportunities based on historical conversion rates." Each recommendation has: action, projected impact, confidence level, reasoning. User can approve/dismiss.
5. **Campaign health score** — composite metric factoring CTR trends, CPC trends, conversion rate, budget pacing, audience fatigue indicators.

**ClickHouse schema (campaign metrics):**

```sql
CREATE TABLE campaign_metrics (
    tenant_id UUID,
    campaign_id UUID,
    platform LowCardinality(String), -- 'linkedin', 'meta', 'google'
    platform_campaign_id String,
    date Date,
    spend Decimal(12, 2),
    impressions UInt64,
    clicks UInt64,
    conversions UInt32,
    ctr Float32,
    cpc Decimal(8, 2),
    cpm Decimal(8, 2),
    roas Float32,
    ingested_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(ingested_at)
ORDER BY (tenant_id, campaign_id, platform, date);
```

### 3.5 Revenue Attribution

**This is the key differentiator.** Most paid media tools stop at ad platform metrics. PaidEdge ties campaigns to actual CRM revenue.

**Data flow:** Salesforce or HubSpot → RudderStack Cloud Sources → ClickHouse.

**What gets pulled from CRM:**

- Opportunities / Deals: amount, stage, close date, won/lost status, associated contacts
- Contacts / Leads: email, company, lead source, UTM parameters captured at form fill
- Activities: relevant touchpoints

**Attribution logic:**

1. Person fills out form on PaidEdge landing page. UTM params + click ID captured. Person self-identifies (email, name, company).
2. RudderStack `identify()` call merges their anonymous session history with their known identity.
3. Person enters CRM as lead/contact (either via PaidEdge webhook or via existing CRM workflow).
4. When opportunity is created and progresses through stages, PaidEdge matches the contact back to the originating campaign via UTM/click ID.
5. Attribution views in PaidEdge show: this campaign → these leads → these opportunities → $X pipeline → $Y closed-won.

**Revenue attribution views:**

- **Cost-per-opportunity:** total campaign spend / opportunities created. This is NOT available in any ad platform natively.
- **Cost-per-closed-won:** total campaign spend / deals won. The ultimate ROI metric.
- **Pipeline influenced:** campaigns that touched contacts involved in open opportunities, even if not first-touch.
- **Closed-won lookalike generation:** take the firmographic profile of closed-won companies, feed back into audience building (stage 1). Closed loop.
- **Closed-lost analysis:** what do companies that didn't close look like? Build exclusion segments. Feed back into audience building.

**ClickHouse schema (CRM data):**

```sql
CREATE TABLE crm_opportunities (
    tenant_id UUID,
    opportunity_id String,
    contact_email String,
    company_domain String,
    amount Decimal(12, 2),
    stage LowCardinality(String),
    is_won UInt8,
    is_lost UInt8,
    close_date Date,
    created_at DateTime,
    source_campaign_id Nullable(UUID), -- matched PaidEdge campaign
    source_utm_params Nullable(String),
    ingested_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(ingested_at)
ORDER BY (tenant_id, opportunity_id);
```

---

## 4. What's Explicitly NOT in the Product

These are conscious exclusions, not oversights:

| Exclusion | Reasoning |
|-----------|-----------|
| Person-level website visitor deanonymization | Not core, not for competitive parity. HockeyStack (closest comp) doesn't do this natively either — they say "BYO Vector." If a customer wants RB2B or Vector, they install it themselves. PaidEdge does company-level only via Clay web intent for designated pages. |
| Intent data (TrustRadius, Bombora) | Too expensive for V1. TrustRadius via Clay = 10 credits/result. Direct deals require annual contracts. Listed as "coming soon" on roadmap. |
| Outbound email sequencing | PaidEdge is a paid advertising platform. It can hand off leads to Outreach, Salesloft, Apollo, or similar. It does not send cold email. |
| CRM replacement | PaidEdge reads from Salesforce/HubSpot. It does not replace them. |
| Global asset libraries | Assets are campaign-specific, generated on demand per campaign. No pre-created lead magnet library. Client onboarding inputs (testimonials, case studies, brand guidelines) are the raw material, not finished assets. |
| Ad platform management | PaidEdge is not a full ad platform manager (not replacing LinkedIn Campaign Manager). It pushes audiences, tracks performance, and attributes revenue. Bid management, A/B testing within platforms, etc. stay in native UIs for now. |

---

## 5. BYO Integrations (Supported, Not Provided)

PaidEdge supports optional integrations that customers bring themselves. Nothing breaks without them — they add enrichment layers:

| Integration | What It Adds | How It Connects |
|-------------|-------------|----------------|
| RB2B / Vector / Warmly | Person-level visitor identification. Surfaces "Identified Visitors" breakout view within campaigns — who clicked but didn't convert. | Customer installs their pixel. Webhook fires to PaidEdge FastAPI endpoint. Data written to ClickHouse, joined to campaign via UTM/click ID. |
| 6sense / Demandbase | Account-level intent enrichment if customer already has a subscription. | API key stored in tenant config. PaidEdge queries on demand or ingests via webhook. |
| Sendoso | Incentive-attached campaign offers (gift cards, swag, etc.). | API integration triggered from campaign config when incentive is enabled. |

---

## 6. Data Architecture

### 6.1 Infrastructure Stack

| Component | Role | Details |
|-----------|------|---------|
| **ClickHouse** | Metrics warehouse | Campaign metrics (from ad platform APIs), CRM opportunity/contact data, behavioral events (from RudderStack), web intent resolution results. Single source of truth for all analytics, attribution, and AI recommendation queries. |
| **Supabase** | Entity DB + Auth + Multi-tenant | PostgreSQL. Multi-tenant auth (organizations table, user → org membership). Audience segment definitions, campaign metadata, tenant context (onboarding inputs), provider configs (API keys per tenant for ad platforms, CRM). Schemas: `public` (auth/core), `entities` (companies, people), `ops` (campaigns, segments, configs). |
| **RudderStack** | Event ingestion + Cloud Sources | **JS SDK:** Installed on customer's website + PaidEdge-generated landing pages. Captures page views, form fills, CTA clicks. Sends to ClickHouse destination. **Cloud Sources:** Pull data from LinkedIn Ads API, Meta Ads API, Google Ads API, Salesforce, HubSpot into ClickHouse on schedule. |
| **BlitzAPI** | Enrichment engine | Unlimited data usage. Company enrichment, person search, firmographic matching, job title resolution, lookalike building. Core of the audience building engine. |
| **Clay** | Orchestration + web intent | Web intent deanonymization (company-level, ~4 credits/lookup via IP waterfall). LinkedIn post engager extraction (alternative to Trigify). Legacy plan retained for TrustRadius access (available but expensive). Modern plan features (Clay Ads, web intent) require migration — evaluate as needed. |
| **Trigify** | Social signal extraction | LinkedIn post engager extraction (likers/commenters). PAYG at $0.012/credit. Open API. Primary tool for this workflow due to cost efficiency. |
| **Claude API** | AI layer | Campaign recommendations, asset generation (lead magnets, landing pages, ad copy, email), natural language audience queries, performance analysis, health scoring. Model: claude-sonnet-4-20250514 for speed-sensitive tasks, claude-opus-4-6 for complex analysis/generation. |
| **FastAPI** | Backend API | PaidEdge API layer. Handles: enrichment fan-out (BlitzAPI, Clay, Trigify), webhook ingestion (RudderStack events, BYO integrations), campaign orchestration, ad platform API calls, AI prompt routing. Python. |
| **Railway** | Hosting | All services hosted on Railway. FastAPI backend, frontend, worker processes. |
| **Doppler** | Secrets | Secret and credential management. Per-environment (dev, staging, prod). Tenant-specific API keys stored in Supabase `provider_configs`, not Doppler. |
| **Trigger.dev** | Async job orchestration | Scheduled tasks: audience segment refresh (daily/weekly delta runs against BlitzAPI), ad platform metric ingestion, CRM data sync, AI recommendation generation. Event-driven tasks: web intent lookup on page visit, real-time alert generation. |

### 6.2 Data Flow Diagram

```
                                    ┌─────────────────────┐
                                    │   AD PLATFORMS       │
                                    │  (LinkedIn, Meta,    │
                                    │   Google Ads)        │
                                    └──────────┬──────────┘
                                               │ API pull (RudderStack Cloud Sources)
                                               ▼
┌──────────────┐   JS SDK events    ┌─────────────────────┐    destination    ┌──────────────┐
│ CUSTOMER     │───────────────────▶│   RUDDERSTACK        │────────────────▶│  CLICKHOUSE   │
│ WEBSITE      │                    │                      │                  │  (warehouse)  │
└──────────────┘                    └──────────┬──────────┘                  └──────┬───────┘
                                               │                                    │
┌──────────────┐   JS SDK events               │ Cloud Sources                      │ queries
│ PAIDEDGE     │───────────────────▶           │                                    ▼
│ LANDING      │                    ┌──────────┴──────────┐                  ┌──────────────┐
│ PAGES        │                    │   CRM               │                  │  FASTAPI     │
└──────────────┘                    │  (Salesforce/        │                  │  BACKEND     │
                                    │   HubSpot)          │                  └──────┬───────┘
                                    └─────────────────────┘                         │
                                                                                    │ reads/writes
┌──────────────┐   enrichment API                                            ┌──────┴───────┐
│  BLITZAPI    │◀────────────────────────────────────────────────────────────│  SUPABASE    │
└──────────────┘                                                             │  (entities,  │
┌──────────────┐   web intent / engagers                                     │   segments,  │
│  CLAY        │◀────────────────────────────────────────────────────────────│   campaigns) │
└──────────────┘                                                             └──────────────┘
┌──────────────┐   engager extraction
│  TRIGIFY     │◀────────────────────────────────────────────────────────────
└──────────────┘
┌──────────────┐   asset generation, recommendations
│  CLAUDE API  │◀────────────────────────────────────────────────────────────
└──────────────┘
```

### 6.3 Multi-Tenancy Model

- **Organizations table** in Supabase: each tenant (customer or agency client) is an organization.
- **User membership:** users belong to one or more organizations. Role-based (admin, member, viewer).
- **Provider configs:** per-organization API credentials for ad platforms (LinkedIn, Meta, Google Ads), CRM (Salesforce OAuth tokens, HubSpot API keys), optional BYO integrations (RB2B webhook URL, etc.). Stored in Supabase `organizations.provider_configs` (JSONB, encrypted at rest).
- **Data isolation:** all ClickHouse queries filtered by `tenant_id`. All Supabase queries use RLS policies on `tenant_id`.
- **RudderStack sources:** one RudderStack source per tenant (or shared source with tenant_id property on all events). TBD on exact approach — shared source is simpler, per-tenant is cleaner for customer-facing "install this snippet" flow.

---

## 7. Frontend

### 7.1 Navigation Structure

```
Sidebar:
├── Dashboard (signal cards + KPI overview)
├── Audiences (segment list, builder, detail views)
├── Campaigns (list, create, detail with analytics)
├── Analytics (cross-campaign, cross-platform views)
├── Attribution (revenue attribution, pipeline views)
└── Settings
    ├── Organization
    ├── Integrations (CRM, ad platforms, BYO)
    ├── Brand & Content (onboarding inputs)
    └── Team
```

### 7.2 Key Pages

**Dashboard:** Signal cards in a grid/list. Each card: icon, title ("34 VPs of Engineering new in role"), count, freshness indicator, "Activate → Campaign" button. Also: KPI summary cards (total active campaigns, total spend this month, pipeline influenced, closed-won attributed).

**Audiences:** List of saved segments with member count, last refreshed, status. Detail view: member list (companies/people), filters applied, export option. Builder: chat interface + structured filter UI. Either path produces a segment definition.

**Campaign Create Flow:** Step 1: Select audience → Step 2: Generate/review assets (lead magnet, landing page, ad copy) → Step 3: Select platforms + budget → Step 4: Review & launch. All steps have AI assistance via chat sidebar.

**Campaign Detail:** Tabs: Overview (KPI cards + time series), Platform Breakdown, Assets, Audience, Attribution (leads generated, opportunities, revenue). AI recommendations panel.

**Attribution:** Funnel visualization: campaigns → leads → opportunities → closed-won. Filterable by campaign, time period, platform. Cost-per-opportunity and cost-per-closed-won as headline metrics.

### 7.3 Tech Stack — Frontend

- **Framework:** React (Next.js or Vite — TBD)
- **Styling:** Tailwind CSS
- **Charts:** Recharts or Chart.js
- **State:** React Query for server state, Zustand or similar for client state
- **Auth:** Supabase Auth (email/password + Google OAuth)
- **Chat interface:** Custom component hitting Claude API via FastAPI backend

---

## 8. Competitive Landscape

| Competitor | What They Do | Price | PaidEdge Differentiator |
|-----------|-------------|-------|------------------------|
| **HockeyStack** | Multi-touch attribution, journey analytics, account scoring. Does NOT build audiences, generate assets, or launch campaigns. Company-level visitor ID only (BYO Vector for person-level). | ~$28K/yr median, custom quotes, starts ~$2,200/mo | PaidEdge includes attribution AND audience building, asset generation, and campaign launch. Full loop, not just analytics. |
| **Propensity** | ABM platform with Bombora intent data, omnichannel campaign execution (display, LinkedIn, Meta, email, direct mail), contact-level attribution. Walled garden — uses own intent data, own ad network, own creative. | $1K–$4K/mo (Essential → Unlimited) | PaidEdge is composable — sits on customer's own ad accounts, uses open data sources (BlitzAPI), gives more control and transparency. Not locked into Propensity's ad network. |
| **Metadata.io** | Demand gen platform for B2B. Campaign execution + audience building. Now part of Demandbase. | Enterprise pricing (acquired) | PaidEdge adds AI-native asset generation and CRM revenue attribution. Independent product, not part of enterprise ABM suite. |
| **Clay** | Data orchestration and enrichment. Powerful workflow builder but is a spreadsheet UI, not a campaign platform. Expensive at scale for intent/ads features (Growth plan $495+/mo, Clay Ads requires modern plan). | $185–$2,975/mo depending on actions/credits | PaidEdge uses Clay as infrastructure (web intent, engager extraction) but wraps it in purpose-built demand gen UI. User never sees Clay. |
| **Triple Whale / Whatagraph** | Ad analytics and reporting dashboards. No audience building, no asset generation, no CRM attribution. | $100–$500/mo | PaidEdge does everything they do (analytics) plus everything they don't (audience building, asset gen, launch, attribution). |

---

## 9. Business Model

**Pricing:** $25,000/year (~$2,083/mo). Will underprice initially to acquire first customers and generate cash flow.

**Data costs absorbed by PaidEdge per customer (estimated):**

| Cost | Monthly Estimate |
|------|-----------------|
| BlitzAPI (unlimited enrichment) | Fixed cost, spread across customers |
| Clay web intent (~4 credits/lookup, few hundred lookups/mo) | ~$40–100/mo |
| Trigify LinkedIn engager extraction | ~$20–50/mo |
| Claude API (asset generation, recommendations) | ~$50–150/mo |
| ClickHouse compute | Shared infrastructure |
| **Total estimated per-customer data cost** | **<$500/mo** |

At $2,083/mo revenue per customer, gross margin is ~75%+ on data costs.

**Data costs NOT absorbed (customer pays or future PaidEdge premium tier):**

- TrustRadius intent data (future — premium tier or direct customer data deal)
- Person-level visitor identification (BYO — customer pays RB2B/Vector directly)
- Full Clay Ads audience sync (requires customer's own Clay Growth plan, or PaidEdge builds direct platform API integrations)

---

## 10. Build Plan

### 10.1 Build Roles

| Role | Tool | Responsibility |
|------|------|---------------|
| Primary builder | Perplexity Computer | Scaffold multi-tenant app, ClickHouse schema, RudderStack config, frontend dashboard, ad platform integrations, FastAPI backend. Concentrated build sprints. |
| Planning + project management | Claude Code | Decompose this PRD into Linear milestones/epics/tasks. Code review. Refinement and debugging of what Perplexity builds. Ongoing Linear updates. |
| Research enrichment | Parallel.ai / OpenClaw / NemoClaw | Deep research workflows for audience signals ("companies that have X on their site"). Runtime research agents. |
| Project state | Linear | Source of truth. Milestones, epics, tasks. Updated continuously. |

### 10.2 Perplexity Computer Budget

- **This month (March 2026):** 50,000 credits (bonus month)
- **Ongoing:** 15,000 credits/mo
- **Implication:** Front-load the heaviest build work into March. Use the 50K credits for full app scaffold, schema, core integrations. Ongoing 15K/mo for iteration, new features, bug fixes.

### 10.3 Milestone Sketch

To be decomposed into full Linear epics/tasks. This is the high-level phasing:

**M1 — Infrastructure Foundation**
- ClickHouse schema (campaign_metrics, crm_opportunities, behavioral_events, audience_segment_members)
- Supabase multi-tenant setup (organizations, users, memberships, provider_configs, audience_segments, campaigns, tenant_context)
- RudderStack sources configured (JS SDK source, ad platform Cloud Sources, CRM Cloud Sources)
- FastAPI skeleton with auth middleware, tenant resolution, health checks
- Basic frontend shell with auth flow, sidebar navigation, routing
- Railway deployment pipeline
- Doppler secret management setup

**M2 — Audience Engine**
- BlitzAPI integration (company enrichment, person search, firmographic matching)
- Signal card framework (pluggable — each signal type is a module)
- Trigger.dev scheduled tasks for delta detection (new in role, departed, promoted, raised money)
- Clay web intent integration (RudderStack event → Clay lookup → ClickHouse write → signal card)
- Trigify API integration (LinkedIn post engager extraction)
- Lookalike segment builder (CRM closed-won → firmographic profile → BlitzAPI matching)
- Chat-driven audience builder (Claude API + structured query generation)
- Audience list UI (segments, member counts, detail views)

**M3 — Campaign Builder + Asset Generation**
- Campaign creation flow (select audience → generate assets → select platforms → launch)
- Claude API integration for asset generation (lead magnets as PDF, landing page HTML, ad copy per platform, email copy)
- Landing page hosting (PaidEdge subdomain, RudderStack JS SDK baked in, form capture)
- Audience push to ad platforms (initial: CSV export formatted per platform; then: direct API or Clay Ads webhook)
- Campaign data model and CRUD
- Asset preview and editing UI

**M4 — Analytics + Attribution**
- Ad platform API ingestion: LinkedIn Ads API, Meta Marketing API, Google Ads API → RudderStack → ClickHouse
- Campaign analytics dashboard (KPIs, time series, platform breakdown)
- Cross-platform comparison views
- CRM ingestion: Salesforce API, HubSpot API → RudderStack → ClickHouse
- UTM/click ID → CRM contact → opportunity matching logic
- Revenue attribution views (cost-per-opportunity, cost-per-closed-won, pipeline influenced)
- Funnel visualization (campaigns → leads → opportunities → revenue)

**M5 — AI Recommendations + Polish**
- Performance analysis agent (Claude API querying ClickHouse, generating actionable recommendations)
- Budget optimization suggestions
- Audience refinement recommendations ("your best-performing segment shares these traits")
- Campaign health scoring (composite metric)
- Approve/dismiss/implement recommendation flow
- Dashboard polish, loading states, error handling, empty states

**M6 — First Customer Live**
- End-to-end testing with real ad platform accounts
- Onboarding flow (connect CRM, connect ad platforms, install site snippet, upload brand context)
- Documentation / help content
- Billing integration (Stripe)
- First customer deployment and support

---

## 11. Open Questions

These need resolution during build planning, not before:

1. **Ad platform audience push mechanism:** Build direct LinkedIn/Meta/Google Ads API integrations (requires OAuth partner approval, significant dev work) or rely on Clay Ads (requires modern plan at $495+/mo) or CSV export (manual, but ships fast)?
2. **Trigify vs. Clay for LinkedIn engagers:** Trigify is cheaper (PAYG $0.012/credit) and has open API. Clay is already in the stack. Possibly use both — Trigify as primary, Clay as fallback.
3. **TrustRadius direct partnership:** When revenue justifies, negotiate direct API access for "companies searching for X" signal. Unknown pricing and timeline.
4. **Landing page hosting:** PaidEdge-hosted subdomain (simplest), customer CNAME subdomain (more professional), or integrate with Unbounce/Webflow (more complex)?
5. **Video/motion graphic generation:** Scope for V1? Probably out. Revisit for V2 when core loop is proven.
6. **RudderStack source model:** One shared source with tenant_id on events (simpler infra) or one source per tenant (cleaner data isolation, easier "install this snippet" customer experience)?
7. **Frontend framework:** Next.js (SSR, routing built in, Vercel deployment option) vs. Vite + React Router (lighter, Railway deployment). Perplexity Computer may have a preference.
8. **Email resolution for audience push:** Prospeo API vs. Clay credits vs. other email finding service. Match rates and cost per resolution need testing.
9. **Perplexity Computer sprint planning:** Given 50K credits this month and 15K/mo ongoing, what's the optimal sequencing? Likely: M1 + M2 scaffold in March, M3 + M4 in April, M5 + M6 in May.

---

## 12. Success Metrics

How we know PaidEdge is working:

| Metric | Target |
|--------|--------|
| Time from login to campaign launch | <30 minutes (vs. hours/days with current tooling) |
| Audience signals surfaced on login | 5+ actionable signal cards per tenant |
| Campaign-to-revenue attribution | 100% of PaidEdge-launched campaigns trackable to CRM outcomes |
| Customer data cost per tenant | <$500/mo absorbed |
| First paying customer | Within 60 days of M6 completion |
| Annual contract value | $25K minimum |

---

*This document is the source of truth for PaidEdge product definition. It should be decomposed into Linear milestones, epics, and tasks via Claude Code. All build decisions should reference this document.*
