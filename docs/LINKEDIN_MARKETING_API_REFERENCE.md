# LinkedIn Marketing API — Comprehensive Reference

> **Purpose:** Everything needed to build a LinkedIn Ads integration for PaidEdge, a multi-tenant B2B SaaS platform managing paid advertising campaigns on behalf of multiple client organizations.
>
> **API Base URL:** `https://api.linkedin.com/rest/`
>
> **Current API Version:** `202603` (YYYYMM format)
>
> **Required Headers on All Requests:**
> ```
> Authorization: Bearer {ACCESS_TOKEN}
> LinkedIn-Version: 202603
> X-Restli-Protocol-Version: 2.0.0
> Content-Type: application/json
> ```

---

## Table of Contents

1. [Authentication & OAuth 2.0](#1-authentication--oauth-20)
2. [Account Structure](#2-account-structure)
3. [Matched Audiences / Custom Audiences](#3-matched-audiences--custom-audiences)
4. [Programmatic Ad Creation & Upload](#4-programmatic-ad-creation--upload)
5. [Campaign Management](#5-campaign-management)
6. [Lead Gen Forms](#6-lead-gen-forms)
7. [Conversions API (CAPI)](#7-conversions-api-capi)
8. [Reporting & Analytics](#8-reporting--analytics)
9. [Rate Limits](#9-rate-limits)
10. [Python Libraries](#10-python-libraries)
11. [Common Gotchas](#11-common-gotchas)

---

## 1. Authentication & OAuth 2.0

### 1.1 Overview

LinkedIn Marketing APIs exclusively use **3-legged OAuth 2.0** (Authorization Code Flow). **2-legged OAuth (client credentials) is explicitly not available for any Marketing API use case.** All permission scopes for advertising are member permissions requiring explicit member consent.

### 1.2 Full 3-Legged OAuth 2.0 Authorization Code Flow

#### Step 1: Configure Your Application

Register at [developer.linkedin.com](https://www.linkedin.com/developers/apps) to get:
- **Client ID** (API Key)
- **Client Secret**

Add your redirect URI(s) under the **Auth** tab. Rules:
- Must be absolute HTTPS URLs (e.g., `https://app.example.com/auth/callback`)
- Cannot contain query parameters or `#` fragments
- Parameters in request redirect_uri are ignored at match time

#### Step 2: Request an Authorization Code

Redirect the member's browser to:

```
GET https://www.linkedin.com/oauth/v2/authorization
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `response_type` | Yes | Must be `code` |
| `client_id` | Yes | Your app's Client ID |
| `redirect_uri` | Yes | Must exactly match a registered redirect URI |
| `scope` | Yes | URL-encoded space-delimited list of permissions |
| `state` | Recommended | CSRF protection token (hard-to-guess unique string) |

**curl:**

```bash
curl -G "https://www.linkedin.com/oauth/v2/authorization" \
  --data-urlencode "response_type=code" \
  --data-urlencode "client_id=YOUR_CLIENT_ID" \
  --data-urlencode "redirect_uri=https://app.example.com/auth/callback" \
  --data-urlencode "state=RANDOM_CSRF_TOKEN" \
  --data-urlencode "scope=r_ads rw_ads r_ads_reporting r_organization_social"
```

**Python:**

```python
import urllib.parse
import secrets

BASE_URL = "https://www.linkedin.com/oauth/v2/authorization"
state = secrets.token_urlsafe(16)

params = {
    "response_type": "code",
    "client_id": "YOUR_CLIENT_ID",
    "redirect_uri": "https://app.example.com/auth/callback",
    "state": state,
    "scope": "r_ads rw_ads r_ads_reporting r_organization_social w_member_social",
}

auth_url = BASE_URL + "?" + urllib.parse.urlencode(params)
# Redirect user to auth_url
# Store state in session for CSRF verification later
```

**Successful redirect back:**
```
https://app.example.com/auth/callback
  ?code=AQTQmah11lalyH65DAIivsjsAQV5P...
  &state=RANDOM_CSRF_TOKEN
```

Authorization code properties: 30-minute lifespan, single use.

**Failed redirect:**
```
https://app.example.com/auth/callback
  ?error=user_cancelled_authorize
  &error_description=The+member+refused+to+authorize+...
  &state=RANDOM_CSRF_TOKEN
```

#### Step 3: Exchange Authorization Code for Access Token

```
POST https://www.linkedin.com/oauth/v2/accessToken
Content-Type: application/x-www-form-urlencoded
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `grant_type` | Yes | `authorization_code` |
| `code` | Yes | The authorization code from step 2 |
| `client_id` | Yes | Your Client ID |
| `client_secret` | Yes | Your Client Secret |
| `redirect_uri` | Yes | Same redirect URI used in step 2 |

**curl:**

```bash
curl -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "code=AQTQmah11lalyH65DAIivsjsAQV5P..." \
  --data-urlencode "client_id=YOUR_CLIENT_ID" \
  --data-urlencode "client_secret=YOUR_CLIENT_SECRET" \
  --data-urlencode "redirect_uri=https://app.example.com/auth/callback"
```

**Python:**

```python
import requests

def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    response = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uri": redirect_uri,
        },
    )
    response.raise_for_status()
    return response.json()
```

**Response:**

```json
{
  "access_token": "AQUvlL_DYEzvT2wz1QJiEPeLioeA...",
  "expires_in": 5184000,
  "refresh_token": "AQWAft_WjYZKwuWXLC5hQlghgTam...",
  "refresh_token_expires_in": 525600,
  "scope": "r_ads,rw_ads,r_ads_reporting"
}
```

#### Step 4: Make Authenticated API Calls

```bash
curl -X GET "https://api.linkedin.com/rest/adAccounts?q=search" \
  -H "Authorization: Bearer {ACCESS_TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0"
```

```python
import requests

def call_linkedin_api(access_token: str, endpoint: str) -> dict:
    response = requests.get(
        f"https://api.linkedin.com{endpoint}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )
    response.raise_for_status()
    return response.json()
```

### 1.3 Token Lifetimes and Refresh Mechanics

| Token | Lifespan | Notes |
|-------|----------|-------|
| Authorization code | 30 minutes | Must be exchanged immediately |
| Access token | **60 days** (5,184,000 seconds) | Fixed TTL from issuance |
| Refresh token | **365 days** from initial authorization | TTL does **not** reset on use |

**Critical:** When you use a refresh token to mint a new access token, the refresh token's remaining TTL continues counting down from the original authorization date. It does NOT renew.

Programmatic refresh tokens are available for **Marketing Developer Platform (MDP) partners** — all developers approved for the Advertising API.

#### Refresh Token Exchange

```bash
curl -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=refresh_token" \
  --data-urlencode "refresh_token=AQWAft_WjYZKwuWXLC5hQlghgTam..." \
  --data-urlencode "client_id=YOUR_CLIENT_ID" \
  --data-urlencode "client_secret=YOUR_CLIENT_SECRET"
```

```python
def refresh_access_token(refresh_token: str) -> dict:
    response = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
        },
    )
    response.raise_for_status()
    return response.json()
```

### 1.4 Token Introspection

```bash
curl -X POST "https://www.linkedin.com/oauth/v2/introspectToken" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "client_id=YOUR_CLIENT_ID" \
  --data-urlencode "client_secret=YOUR_CLIENT_SECRET" \
  --data-urlencode "token={ACCESS_TOKEN}"
```

**Response:**

```json
{
  "active": true,
  "client_id": "861hhm46p48to2",
  "authorized_at": 1493055596,
  "created_at": 1493055596,
  "status": "active",
  "expires_at": 1497497620,
  "scope": "r_ads,rw_ads,r_ads_reporting",
  "auth_type": "3L"
}
```

### 1.5 All Advertising Scopes

All Marketing API scopes are **3-legged only** — no 2-legged scopes exist for advertising.

| Scope | Description | Required For |
|-------|-------------|--------------|
| `r_ads` | Read ad accounts, campaigns, creatives (all roles including VIEWER) | Any read access to ads data |
| `rw_ads` | Read + write ad accounts, campaigns, creatives (requires CAMPAIGN_MANAGER+ role) | Creating/updating campaigns |
| `r_ads_reporting` | Read ad analytics reporting data | Analytics/reporting |
| `r_organization_social` | Read organization posts, comments, likes | Reading organic page content |
| `w_member_social` | Post, comment, like on behalf of the authenticated member | Member-level social posting |
| `w_organization_social` | Post, comment, like on behalf of an organization | Organization-level social posting |
| `rw_organization_admin` | Manage organization pages + retrieve reporting | Managing company pages |
| `r_organization_admin` | Read organization pages and reporting data | Read-only org page access |
| `r_basicprofile` | Read member name, photo, headline, profile URL | Basic member identity |
| `rw_dmp_segments` | Create/manage Matched Audiences segments | Matched Audiences API (extra approval required) |
| `rw_conversions` | Upload and manage conversion data | Conversions API |
| `r_marketing_leadgen_automation` | Access lead gen forms and leads | Lead Sync API |

### 1.6 System User vs. Member Tokens

LinkedIn does **not** have a "service account" or "system user" concept. The Marketing API is purely member-token-based:

- All API calls require a **member's access token** obtained via 3-legged OAuth
- The member must hold an appropriate **Ad Account Role** on each account
- There is no way to obtain a token without a real LinkedIn member authenticating

### 1.7 Per-Tenant Token Management for Multi-Tenant SaaS

Each tenant goes through the 3-legged OAuth flow. Store per-tenant:

```python
class LinkedInToken:
    tenant_id: str                       # your internal tenant identifier
    member_urn: str                      # urn:li:person:{id} — from GET /me
    access_token: str                    # ~500 chars, plan for 1000
    access_token_expires_at: datetime    # now + 60 days
    refresh_token: str                   # ~500 chars, plan for 1000
    refresh_token_expires_at: datetime   # initial_auth_date + 365 days
    scope: str                           # comma-separated granted scopes
    created_at: datetime
    updated_at: datetime
```

**Proactive refresh strategy:**

```python
from datetime import datetime, timedelta, timezone

REFRESH_BUFFER_DAYS = 7

def get_valid_access_token(tenant_id: str, token_store) -> str:
    token = token_store.get(tenant_id)
    now = datetime.now(timezone.utc)

    # Check if refresh token itself is about to expire
    if token.refresh_token_expires_at < now + timedelta(days=14):
        raise Exception(
            f"Tenant {tenant_id} refresh token expiring soon — "
            "member must re-authorize via OAuth flow"
        )

    # Proactively refresh before expiry
    if token.access_token_expires_at < now + timedelta(days=REFRESH_BUFFER_DAYS):
        new_token_data = refresh_access_token(token.refresh_token)
        token.access_token = new_token_data["access_token"]
        token.access_token_expires_at = now + timedelta(
            seconds=new_token_data["expires_in"]
        )
        token.refresh_token = new_token_data["refresh_token"]
        # refresh_token_expires_at stays at the original date
        token.updated_at = now
        token_store.save(token)

    return token.access_token
```

**Key multi-tenant considerations:**
- One member can authorize your app multiple times — all produce valid tokens
- If scope changes, all previous tokens for that member/app are invalidated
- Token is tied to a **member**, not an ad account — a member can have roles on multiple accounts
- If a member leaves a company, their token becomes useless for that account even though it's still technically valid
- Use `GET /me` immediately after authorization to capture the `member_urn`

---

## 2. Account Structure

### 2.1 Hierarchy Overview

```
Ad Account  (urn:li:sponsoredAccount:{id})
    └── Campaign Group  (urn:li:sponsoredCampaignGroup:{id})
            └── Campaign  (urn:li:sponsoredCampaign:{id})
                    └── Creative  (urn:li:sponsoredCreative:{id})
```

**Scale limits:**
- Max 5,000 campaigns per ad account (any status)
- Max 1,000 concurrent ACTIVE campaigns per ad account
- Max 2,000 campaigns per non-default campaign group
- Max 15,000 creatives per ad account
- Max 100 creatives per campaign

### 2.2 Ad Accounts

#### List all ad accounts accessible to the authenticated member

```bash
curl -X GET "https://api.linkedin.com/rest/adAccounts?q=search&search=(status:(values:List(ACTIVE)))" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0"
```

```python
def list_ad_accounts(access_token: str, status: str = "ACTIVE") -> dict:
    response = requests.get(
        "https://api.linkedin.com/rest/adAccounts",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        params={
            "q": "search",
            "search": f"(status:(values:List({status})))",
        },
    )
    response.raise_for_status()
    return response.json()
```

**Response:**

```json
{
  "elements": [
    {
      "test": false,
      "currency": "USD",
      "id": 507404993,
      "name": "Dunder Mifflin Account",
      "reference": "urn:li:organization:2414183",
      "servingStatuses": ["BILLING_HOLD"],
      "status": "ACTIVE",
      "type": "BUSINESS"
    }
  ]
}
```

#### Discover accounts via authenticated user's roles

```bash
curl -X GET "https://api.linkedin.com/rest/adAccountUsers?q=authenticatedUser" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0"
```

**Response:**

```json
{
  "elements": [
    {
      "account": "urn:li:sponsoredAccount:516413367",
      "role": "ACCOUNT_BILLING_ADMIN",
      "user": "urn:li:person:K1RwyVNukt"
    },
    {
      "account": "urn:li:sponsoredAccount:516880883",
      "role": "CAMPAIGN_MANAGER",
      "user": "urn:li:person:K1RwyVNukt"
    }
  ]
}
```

### 2.3 Permissions Model — Two Independent Layers

**Layer 1: OAuth Scope** — what the member consented to

| Scope | Access Level |
|-------|-------------|
| `r_ads` | Read-only for all roles including VIEWER |
| `rw_ads` | Read + write (requires CAMPAIGN_MANAGER+ role) |
| `r_ads_reporting` | Read analytics/reporting data |

**Layer 2: Ad Account Role** — what role the member holds on the specific account

| Role | Permissions |
|------|-------------|
| `VIEWER` | View campaign data and reports only |
| `CREATIVE_MANAGER` | View + create/edit creatives |
| `CAMPAIGN_MANAGER` | View + create/edit campaigns and creatives |
| `ACCOUNT_MANAGER` | Campaign management + account settings + user access |
| `ACCOUNT_BILLING_ADMIN` | All above + billing (one per account) |

Effective permission = intersection of scope and role. The more restrictive always wins.

### 2.4 Campaign Groups

```bash
curl -X GET \
  "https://api.linkedin.com/rest/adAccounts/506223315/adCampaignGroups?q=search&search=(status:(values:List(ACTIVE,DRAFT)))" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0"
```

#### Create a campaign group

```bash
curl -X POST "https://api.linkedin.com/rest/adAccounts/512352200/adCampaignGroups" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "account": "urn:li:sponsoredAccount:512352200",
    "name": "Q2 Lead Gen Group",
    "runSchedule": { "start": 1700000000000, "end": 1710000000000 },
    "status": "ACTIVE",
    "totalBudget": { "amount": "60000.00", "currencyCode": "USD" }
  }'
```

### 2.5 Campaigns

```bash
curl -X GET \
  "https://api.linkedin.com/rest/adAccounts/506333826/adCampaigns?q=search&search=(status:(values:List(ACTIVE)))" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0"
```

### 2.6 Creatives

| Creative Type | Content Reference |
|---------------|-------------------|
| Sponsored Content (image/video/article) | `urn:li:ugcPost:{id}` or `urn:li:share:{id}` |
| Message Ads / Conversation Ads | `urn:li:adInMailContent:{id}` |
| Text Ads | Inline text content object |
| Dynamic Ads (Follower/Spotlight/Jobs) | Inline dynamic content object |
| Event Ads | `urn:li:event:{id}` (API version 202505+) |

### 2.7 ID Reference

| Level | ID Format | How to Get It |
|-------|-----------|---------------|
| Ad Account | `urn:li:sponsoredAccount:{id}` | `GET /adAccountUsers?q=authenticatedUser` |
| Campaign Group | `urn:li:sponsoredCampaignGroup:{id}` | `GET /adAccounts/{id}/adCampaignGroups?q=search` |
| Campaign | `urn:li:sponsoredCampaign:{id}` | `GET /adAccounts/{id}/adCampaigns?q=search` |
| Creative | `urn:li:sponsoredCreative:{id}` | `GET /adAccounts/{id}/adCreatives?q=search` |
| Organization | `urn:li:organization:{id}` | `GET /organizationAcls?q=roleAssignee` |
| Member | `urn:li:person:{id}` | `GET /me` |

### 2.8 Access Tiers

| Tier | Create Ad Accounts | Edit Ad Accounts | Read |
|------|--------------------|------------------|------|
| **Development** | 1 test account (API) | Up to 5 ad accounts | Unlimited |
| **Standard** | Unlimited | Unlimited | Unlimited |

Standard tier requires a support ticket with a **video demonstration** of your platform.

---

## 3. Matched Audiences / Custom Audiences

### 3.1 Overview

Matched Audiences let you build custom audiences by uploading company lists or contact lists, matching them against LinkedIn's member profiles. The matched output becomes an `adSegment` usable in campaign targeting.

**Access note:** Matched Audiences is a **private API program**. Access to the Marketing API does not automatically grant it. Apply separately. Requires `rw_dmp_segments` scope.

### 3.2 Architecture: DMP Segments and Ad Segments

- **DMP Segment** — your staging bucket where you push data (companies or users)
- **Ad Segment** — the matched output, created automatically by LinkedIn once matching completes. Referenced by `destinationSegmentId`.

State machine:
```
BUILDING → READY → UPDATING → READY
         → FAILED
         → ARCHIVED (unused 30 days)
         → EXPIRED (90 days after archived)
```

### 3.3 Two Upload Methods

#### Method A: Streaming API (Recommended)

For dynamic, real-time updates. Can add or remove incrementally. Running campaigns are **not paused** during updates. Initial matching takes up to 48 hours; subsequent updates are near-real-time.

**Limits:**
- Up to 5,000 records per batch API call
- Rate limit: 600 requests/minute for `/users`, 300 requests/minute for `/companies`

#### Method B: List Upload (CSV)

For bulk, one-time uploads. Simple but less flexible — replaces the entire audience. Maximum 300,000 records per file.

### 3.4 Create a DMP Segment

```bash
curl -X POST "https://api.linkedin.com/rest/dmpSegments" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "name": "Q2 Target Companies",
    "type": "COMPANY",
    "account": "urn:li:sponsoredAccount:507404993",
    "sources": ["FIRST_PARTY"]
  }'
```

```python
def create_dmp_segment(access_token: str, account_id: int, name: str,
                       segment_type: str = "COMPANY") -> dict:
    response = requests.post(
        "https://api.linkedin.com/rest/dmpSegments",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json={
            "name": name,
            "type": segment_type,  # "COMPANY" or "USER"
            "account": f"urn:li:sponsoredAccount:{account_id}",
            "sources": ["FIRST_PARTY"],
        },
    )
    response.raise_for_status()
    return response.json()
```

### 3.5 Upload Company Lists (Streaming)

```bash
curl -X POST "https://api.linkedin.com/rest/dmpSegments/{segmentId}/companies" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "elements": [
      {
        "action": "ADD",
        "companyIdentifiers": {
          "companyName": "Acme Corp",
          "companyDomain": "acme.com"
        }
      },
      {
        "action": "ADD",
        "companyIdentifiers": {
          "companyName": "Globex Corporation",
          "companyDomain": "globex.com"
        }
      }
    ]
  }'
```

```python
def stream_companies(access_token: str, segment_id: str,
                     companies: list[dict], action: str = "ADD") -> dict:
    elements = [
        {
            "action": action,  # "ADD" or "REMOVE"
            "companyIdentifiers": company,
        }
        for company in companies
    ]
    response = requests.post(
        f"https://api.linkedin.com/rest/dmpSegments/{segment_id}/companies",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json={"elements": elements},
    )
    response.raise_for_status()
    return response.json()
```

### 3.6 Upload Contact Lists (Hashed Emails)

**Critical:** Emails must be **lowercased and whitespace-stripped before hashing**. SHA256 is required for CSV; SHA256 and SHA512 accepted for streaming.

```bash
curl -X POST "https://api.linkedin.com/rest/dmpSegments/{segmentId}/users" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "elements": [
      {
        "action": "ADD",
        "userIdentifiers": {
          "hashedEmail": {
            "hashType": "SHA256",
            "hashValue": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
          }
        }
      }
    ]
  }'
```

```python
import hashlib

def hash_email(email: str) -> str:
    """Lowercase, strip whitespace, then SHA256 hash."""
    normalized = email.lower().strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def stream_contacts(access_token: str, segment_id: str,
                    emails: list[str], action: str = "ADD") -> dict:
    elements = [
        {
            "action": action,
            "userIdentifiers": {
                "hashedEmail": {
                    "hashType": "SHA256",
                    "hashValue": hash_email(email),
                }
            },
        }
        for email in emails
    ]
    response = requests.post(
        f"https://api.linkedin.com/rest/dmpSegments/{segment_id}/users",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json={"elements": elements},
    )
    response.raise_for_status()
    return response.json()
```

### 3.7 CSV List Upload Flow

```python
# Step 1: Generate upload URL
response = requests.post(
    "https://api.linkedin.com/rest/dmpSegments?action=generateUploadUrl",
    headers={
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": "202603",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    },
    json={"segmentId": f"urn:li:dmpSegment:{segment_id}"},
)
upload_url = response.json()["uploadUrl"]

# Step 2: PUT the CSV to the pre-signed URL
import httpx
with open("audience.csv", "rb") as f:
    httpx.put(upload_url, content=f.read())
```

### 3.8 Match Rates

- Company matching by domain: typically **60-80%** match rates
- Company matching by name only: lower, **30-50%** due to name variations
- Email matching: **20-40%** typical (LinkedIn members with verified email)
- LinkedIn member ID matching: nearly **100%** (direct match)

### 3.9 Minimum Audience Size

**300 matched members** minimum for a segment to be usable in campaign targeting. Below this threshold, LinkedIn blocks usage with `AUDIENCE_SIZE_TOO_SMALL` error.

### 3.10 Status Polling

```bash
curl -X GET "https://api.linkedin.com/rest/dmpSegments/{segmentId}" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0"
```

```python
def check_segment_status(access_token: str, segment_id: str) -> dict:
    response = requests.get(
        f"https://api.linkedin.com/rest/dmpSegments/{segment_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )
    response.raise_for_status()
    data = response.json()
    # Key fields: status, matchedMemberCount, destinationSegmentId
    return data
```

### 3.11 Delete a Segment

```bash
curl -X DELETE "https://api.linkedin.com/rest/dmpSegments/{segmentId}" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0"
```

---

## 4. Programmatic Ad Creation & Upload

### 4.1 Sponsored Content — Single Image

#### Image Specs

| Spec | Requirement |
|------|-------------|
| File format | JPG, PNG, GIF (non-animated) |
| File size | Max 5 MB |
| Recommended dimensions | 1200 x 627 px (1.91:1 ratio) |
| Minimum dimensions | 400 x 400 px |
| Character limits | Headline: 70 chars (200 max), Intro text: 150 chars (600 max), Description: 100 chars (300 max) |

#### Step 1: Upload image asset

```bash
# Register the upload
curl -X POST "https://api.linkedin.com/rest/images?action=initializeUpload" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "initializeUploadRequest": {
      "owner": "urn:li:organization:2414183"
    }
  }'
```

Response includes `uploadUrl` and `image` URN. Upload the binary:

```bash
curl -X PUT "{uploadUrl}" \
  -H "Authorization: Bearer {TOKEN}" \
  --upload-file image.jpg
```

#### Step 2: Create post with image

```bash
curl -X POST "https://api.linkedin.com/rest/posts" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "author": "urn:li:organization:2414183",
    "commentary": "Check out our latest product update!",
    "visibility": "PUBLIC",
    "distribution": {
      "feedDistribution": "NONE",
      "targetEntities": [],
      "thirdPartyDistributionChannels": []
    },
    "content": {
      "media": {
        "title": "Product Update Q2",
        "id": "urn:li:image:C4E22AQHmVLNmZ..."
      }
    },
    "lifecycleState": "PUBLISHED",
    "isReshareDisabledByAuthor": false
  }'
```

#### Step 3: Create creative referencing the post

```bash
curl -X POST "https://api.linkedin.com/rest/adAccounts/{accountId}/adCreatives" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "campaign": "urn:li:sponsoredCampaign:141049524",
    "content": {
      "reference": "urn:li:ugcPost:7012345678901234567"
    },
    "intendedStatus": "ACTIVE"
  }'
```

```python
def create_image_creative(access_token: str, account_id: int,
                          campaign_id: int, post_urn: str) -> dict:
    response = requests.post(
        f"https://api.linkedin.com/rest/adAccounts/{account_id}/adCreatives",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json={
            "campaign": f"urn:li:sponsoredCampaign:{campaign_id}",
            "content": {"reference": post_urn},
            "intendedStatus": "ACTIVE",
        },
    )
    response.raise_for_status()
    return response.json()
```

### 4.2 Sponsored Content — Video

#### Video Specs

| Spec | Requirement |
|------|-------------|
| File format | MP4 |
| File size | 75 KB – 200 MB |
| Duration | 3 seconds – 30 minutes |
| Resolution | 360p – 1080p |
| Aspect ratio | 1:2.4 to 2.4:1 (16:9 recommended) |
| Frame rate | ≤ 30 fps |
| Audio | AAC or MPEG4 |

#### Upload video

```bash
# Step 1: Initialize upload
curl -X POST "https://api.linkedin.com/rest/videos?action=initializeUpload" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "initializeUploadRequest": {
      "owner": "urn:li:organization:2414183",
      "fileSizeBytes": 52428800,
      "uploadCaptions": false,
      "uploadThumbnail": true
    }
  }'
```

Response includes `uploadInstructions` (array of chunk upload URLs for large files) and `video` URN. Upload each chunk in order, then finalize:

```bash
# Step 2: Upload chunks (one per uploadInstruction)
curl -X PUT "{uploadUrl}" \
  -H "Content-Type: application/octet-stream" \
  --upload-file chunk_001.mp4

# Step 3: Finalize
curl -X POST "https://api.linkedin.com/rest/videos?action=finalizeUpload" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "Content-Type: application/json" \
  --data '{
    "finalizeUploadRequest": {
      "video": "urn:li:video:C5F10AQG...",
      "uploadToken": "",
      "uploadedPartIds": ["part1", "part2"]
    }
  }'
```

Then create a post referencing the video URN, and a creative referencing the post.

### 4.3 Sponsored Content — Carousel

#### Specs

| Spec | Requirement |
|------|-------------|
| Number of cards | 2–10 |
| Image per card | 1080 x 1080 px (1:1 ratio), max 10 MB |
| Headline per card | 45 chars recommended |
| Intro text | 150 chars recommended (255 max) |

Each card gets its own image upload and landing page URL. Create as a multi-image post then reference as a creative.

### 4.4 Document Ads (PDF Carousel)

**High-priority format for B2B.**

#### Specs

| Spec | Requirement |
|------|-------------|
| File format | PDF, PPT, PPTX, DOC, DOCX |
| File size | Max 100 MB |
| Page count | Max 300 pages (recommended ≤ 10 for engagement) |
| Dimensions | Flexible; standard slide dimensions recommended |

#### Upload flow

```bash
# Step 1: Initialize document upload
curl -X POST "https://api.linkedin.com/rest/documents?action=initializeUpload" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "initializeUploadRequest": {
      "owner": "urn:li:organization:2414183"
    }
  }'

# Step 2: Upload the document binary
curl -X PUT "{uploadUrl}" \
  -H "Authorization: Bearer {TOKEN}" \
  --upload-file whitepaper.pdf

# Step 3: Create post with document
curl -X POST "https://api.linkedin.com/rest/posts" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "author": "urn:li:organization:2414183",
    "commentary": "Download our 2026 B2B Marketing Guide",
    "visibility": "PUBLIC",
    "distribution": {
      "feedDistribution": "NONE",
      "targetEntities": [],
      "thirdPartyDistributionChannels": []
    },
    "content": {
      "media": {
        "title": "2026 B2B Marketing Guide",
        "id": "urn:li:document:C4D10AQH..."
      }
    },
    "lifecycleState": "PUBLISHED",
    "isReshareDisabledByAuthor": false
  }'
```

```python
def upload_document_ad(access_token: str, org_id: int, file_path: str,
                       title: str, commentary: str) -> str:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": "202603",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    org_urn = f"urn:li:organization:{org_id}"

    # Initialize upload
    init_resp = requests.post(
        "https://api.linkedin.com/rest/documents?action=initializeUpload",
        headers=headers,
        json={"initializeUploadRequest": {"owner": org_urn}},
    )
    init_resp.raise_for_status()
    upload_url = init_resp.json()["value"]["uploadUrl"]
    doc_urn = init_resp.json()["value"]["document"]

    # Upload binary
    with open(file_path, "rb") as f:
        requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {access_token}"},
            data=f.read(),
        )

    # Create post
    post_resp = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers=headers,
        json={
            "author": org_urn,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "NONE",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "media": {"title": title, "id": doc_urn}
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        },
    )
    post_resp.raise_for_status()
    return post_resp.headers.get("x-restli-id")
```

### 4.5 Thought Leader Ads

Boost an employee's organic post as a sponsored ad.

**Requirements:**
- The employee must be an admin of the company page OR explicitly approve the boost
- Requires `w_member_social` scope (the employee's token)
- The post must be a public, original post (not a reshare)

**Flow:**
1. Get the employee's post URN (`urn:li:ugcPost:{id}`)
2. Create a creative in your campaign referencing that post URN
3. LinkedIn will send a notification to the employee requesting approval
4. Once approved, the creative enters review

```bash
curl -X POST "https://api.linkedin.com/rest/adAccounts/{accountId}/adCreatives" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "campaign": "urn:li:sponsoredCampaign:141049524",
    "content": {
      "reference": "urn:li:ugcPost:7012345678901234567"
    },
    "intendedStatus": "ACTIVE"
  }'
```

### 4.6 Sponsored Messaging (Message Ads & Conversation Ads)

#### Message Ads

| Spec | Requirement |
|------|-------------|
| Subject line | Max 60 chars |
| Message body | Max 1,500 chars |
| CTA button text | Max 20 chars |
| Banner image | 300 x 250 px (optional) |
| Sender | Must be a 1st-degree connection or company page |

#### Conversation Ads

| Spec | Requirement |
|------|-------------|
| Opening message | Max 500 chars |
| CTA buttons per message | 2–5 |
| Button text | Max 25 chars |
| Conversation tree depth | Up to 5 levels |

**Targeting constraint:** Messaging ads cannot target the LinkedIn Audience Network (`offsiteDeliveryEnabled` must be false).

**Campaign type:** `SPONSORED_INMAILS`

```bash
# Create InMail content
curl -X POST "https://api.linkedin.com/rest/adInMailContents" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "account": "urn:li:sponsoredAccount:507404993",
    "name": "Q2 Message Ad",
    "subject": "Exclusive offer for your team",
    "htmlBody": "<p>Hi {{FIRST_NAME}},</p><p>We have an exciting offer...</p>",
    "sender": "urn:li:person:abc123",
    "ctaLabel": "Learn More",
    "ctaUrl": "https://example.com/offer"
  }'
```

### 4.7 Lead Gen Form Ads

Lead gen forms attach to Sponsored Content or Message Ad creatives. The creative references both a post and a lead gen form:

```bash
curl -X POST "https://api.linkedin.com/rest/adAccounts/{accountId}/adCreatives" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "campaign": "urn:li:sponsoredCampaign:141049524",
    "content": {
      "reference": "urn:li:ugcPost:7012345678901234567",
      "leadGenerationContext": {
        "leadGenerationFormUrn": "urn:li:leadGenerationForm:123456"
      }
    },
    "intendedStatus": "ACTIVE"
  }'
```

---

## 5. Campaign Management

### 5.1 Create a Campaign

```
POST https://api.linkedin.com/rest/adAccounts/{adAccountId}/adCampaigns
```

**Required fields:**

| Field | Type | Notes |
|---|---|---|
| `account` | URN | `urn:li:sponsoredAccount:{id}` — immutable |
| `campaignGroup` | URN | `urn:li:sponsoredCampaignGroup:{id}` |
| `type` | Enum | `TEXT_AD`, `SPONSORED_UPDATES`, `SPONSORED_INMAILS`, `DYNAMIC` |
| `costType` | Enum | `CPM`, `CPC`, `CPV` |
| `name` | String | Campaign display name |
| `locale` | Object | `{country: "US", language: "en"}` |
| `status` | Enum | `DRAFT`, `ACTIVE`, `PAUSED` |
| `targetingCriteria` | Object | AND/OR boolean expression of facet URNs |
| `offsiteDeliveryEnabled` | Boolean | Must be explicitly set (no default) |
| `dailyBudget` or `totalBudget` | Object | `{amount: string, currencyCode: string}` |
| `unitCost` | Object | Bid amount |

```bash
curl -X POST "https://api.linkedin.com/rest/adAccounts/518121035/adCampaigns" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "account": "urn:li:sponsoredAccount:518121035",
    "campaignGroup": "urn:li:sponsoredCampaignGroup:635137195",
    "name": "Q2 Sponsored Content Campaign",
    "type": "SPONSORED_UPDATES",
    "costType": "CPC",
    "status": "ACTIVE",
    "locale": {"country": "US", "language": "en"},
    "offsiteDeliveryEnabled": false,
    "dailyBudget": {"amount": "50", "currencyCode": "USD"},
    "unitCost": {"amount": "8", "currencyCode": "USD"},
    "targetingCriteria": {
      "include": {
        "and": [
          {"or": {"urn:li:adTargetingFacet:locations": ["urn:li:geo:103644278"]}},
          {"or": {"urn:li:adTargetingFacet:interfaceLocales": ["urn:li:locale:en_US"]}}
        ]
      }
    }
  }'
```

### 5.2 Campaign Objectives

| Objective | Supported Types | Notes |
|-----------|----------------|-------|
| `BRAND_AWARENESS` | SPONSORED_UPDATES, DYNAMIC | CPM only; supports frequency optimization (3-30) |
| `WEBSITE_VISITS` | SPONSORED_UPDATES, TEXT_AD, DYNAMIC, SPONSORED_INMAILS | CPC or CPM |
| `ENGAGEMENT` | SPONSORED_UPDATES | CPC or CPM |
| `VIDEO_VIEWS` | SPONSORED_UPDATES | CPV only; requires video creative |
| `LEAD_GENERATION` | SPONSORED_UPDATES, SPONSORED_INMAILS | Requires lead gen form; `offsiteDeliveryEnabled` must be false |
| `WEBSITE_CONVERSIONS` | SPONSORED_UPDATES, TEXT_AD, DYNAMIC | Requires Insight Tag / Conversions API setup |
| `JOB_APPLICANTS` | SPONSORED_UPDATES, DYNAMIC | Jobs-specific |
| `TALENT_LEADS` | SPONSORED_UPDATES, DYNAMIC | Recruitment-specific |

### 5.3 Targeting Options

| Facet | URN Prefix | Example |
|-------|------------|---------|
| Location | `urn:li:adTargetingFacet:locations` | `urn:li:geo:103644278` (US) |
| Job Title | `urn:li:adTargetingFacet:titles` | `urn:li:title:100` |
| Company | `urn:li:adTargetingFacet:employers` | `urn:li:organization:1337` |
| Industry | `urn:li:adTargetingFacet:industries` | `urn:li:industry:4` |
| Seniority | `urn:li:adTargetingFacet:seniorities` | `urn:li:seniority:8` (VP) |
| Skills | `urn:li:adTargetingFacet:skills` | `urn:li:skill:123` |
| Company Size | `urn:li:adTargetingFacet:staffCountRanges` | `urn:li:staffCountRange:(1,10)` |
| Interface Locale | `urn:li:adTargetingFacet:interfaceLocales` | `urn:li:locale:en_US` |
| Job Function | `urn:li:adTargetingFacet:jobFunctions` | `urn:li:function:12` |
| Degree | `urn:li:adTargetingFacet:degrees` | `urn:li:degree:200` |
| Member Groups | `urn:li:adTargetingFacet:groups` | `urn:li:group:12345` |
| Matched Audiences | `urn:li:adTargetingFacet:matchedAudiences` | `urn:li:adSegment:12345` |

**Targeting structure (AND/OR boolean):**

```json
{
  "targetingCriteria": {
    "include": {
      "and": [
        {"or": {"urn:li:adTargetingFacet:locations": ["urn:li:geo:103644278"]}},
        {"or": {"urn:li:adTargetingFacet:interfaceLocales": ["urn:li:locale:en_US"]}},
        {"or": {"urn:li:adTargetingFacet:seniorities": ["urn:li:seniority:8", "urn:li:seniority:9"]}},
        {"or": {"urn:li:adTargetingFacet:industries": ["urn:li:industry:4", "urn:li:industry:6"]}}
      ]
    },
    "exclude": {
      "or": {
        "urn:li:adTargetingFacet:employers": ["urn:li:organization:1337"]
      }
    }
  }
}
```

### 5.4 Budget and Bid Settings

| Setting | Field | Notes |
|---------|-------|-------|
| Daily budget | `dailyBudget.amount` | Minimum varies by currency (typically $10 USD) |
| Lifetime budget | `totalBudget.amount` | Alternative to daily; minimum typically $100 USD |
| Bid amount | `unitCost.amount` | Manual bid per click/impression/view |
| Cost type | `costType` | `CPC`, `CPM`, `CPV` |
| Bid strategy | `bidStrategy` | `AUTO_BID` (automated), manual (set unitCost) |

### 5.5 Scheduling

```json
{
  "runSchedule": {
    "start": 1700000000000,
    "end": 1710000000000
  }
}
```

- `start`: inclusive, milliseconds since epoch
- `end`: exclusive, optional (omit for open-ended)
- Dayparting is not directly supported via API (managed through Campaign Manager UI)

### 5.6 Campaign Status Lifecycle

```
DRAFT → ACTIVE → PAUSED → ACTIVE (toggle)
                → ARCHIVED (terminal for practical purposes)
                → COMPLETED (budget exhausted or end date passed)
                → CANCELED (terminal)
```

**Update campaign status:**

```bash
curl -X PATCH "https://api.linkedin.com/rest/adAccounts/{accountId}/adCampaigns/{campaignId}" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{"patch": {"$set": {"status": "PAUSED"}}}'
```

```python
def update_campaign_status(access_token: str, account_id: int,
                           campaign_id: int, status: str) -> None:
    response = requests.patch(
        f"https://api.linkedin.com/rest/adAccounts/{account_id}/adCampaigns/{campaign_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json={"patch": {"$set": {"status": status}}},
    )
    response.raise_for_status()
```

---

## 6. Lead Gen Forms

### 6.1 Create a Lead Gen Form

```bash
curl -X POST "https://api.linkedin.com/rest/leadGenerationForms" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "account": "urn:li:sponsoredAccount:507404993",
    "name": "Q2 Whitepaper Download Form",
    "headline": "Get Our Free Guide",
    "description": "Download the 2026 B2B Marketing Guide",
    "privacyPolicyUrl": "https://example.com/privacy",
    "thankYouMessage": "Thanks! Check your email for the download link.",
    "thankYouLandingPageUrl": "https://example.com/thank-you",
    "questions": [
      {
        "fieldType": "FIRST_NAME",
        "required": true
      },
      {
        "fieldType": "LAST_NAME",
        "required": true
      },
      {
        "fieldType": "EMAIL",
        "required": true
      },
      {
        "fieldType": "COMPANY_NAME",
        "required": true
      },
      {
        "fieldType": "JOB_TITLE",
        "required": false
      },
      {
        "fieldType": "CUSTOM",
        "customQuestionText": "What is your biggest marketing challenge?",
        "required": false,
        "answerType": "FREE_TEXT"
      }
    ]
  }'
```

### 6.2 Standard Field Types

| Field Type | Pre-filled From Profile |
|------------|------------------------|
| `FIRST_NAME` | Yes |
| `LAST_NAME` | Yes |
| `EMAIL` | Yes |
| `PHONE_NUMBER` | Yes (if available) |
| `COMPANY_NAME` | Yes |
| `JOB_TITLE` | Yes |
| `JOB_FUNCTION` | Yes |
| `SENIORITY` | Yes |
| `INDUSTRY` | Yes |
| `COMPANY_SIZE` | Yes |
| `CITY` | Yes |
| `STATE` | Yes |
| `COUNTRY` | Yes |
| `WORK_PHONE` | No |
| `GENDER` | No |
| `CUSTOM` | No — requires `customQuestionText` |

### 6.3 Pull Form Submissions

**Lead Sync API** — requires `r_marketing_leadgen_automation` scope.

```bash
curl -X GET "https://api.linkedin.com/rest/leadFormResponses?q=owner&owner=urn:li:sponsoredAccount:507404993&leadGenerationForm=urn:li:leadGenerationForm:123456&submittedAfter=1700000000000" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0"
```

```python
def get_lead_submissions(access_token: str, account_id: int,
                         form_id: int, submitted_after: int = None) -> dict:
    params = {
        "q": "owner",
        "owner": f"urn:li:sponsoredAccount:{account_id}",
        "leadGenerationForm": f"urn:li:leadGenerationForm:{form_id}",
    }
    if submitted_after:
        params["submittedAfter"] = submitted_after  # epoch ms

    response = requests.get(
        "https://api.linkedin.com/rest/leadFormResponses",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        params=params,
    )
    response.raise_for_status()
    return response.json()
```

**Response includes:**
- `submittedAt` — epoch ms timestamp
- `answers` — array of `{fieldType, value}` objects
- `leadGenerationFormUrn` — reference to the form
- `associatedEntity` — the campaign/creative that generated the lead

### 6.4 Webhook Support

LinkedIn supports **Lead Sync webhooks** (push notifications) for real-time lead delivery on Standard tier. On Development tier, webhooks are disabled — you must poll.

To configure webhooks, register a webhook URL in the Developer Portal under your app's settings. LinkedIn sends a POST with the lead data to your URL within seconds of submission.

---

## 7. Conversions API (CAPI)

### 7.1 Overview

LinkedIn's Conversions API (CAPI) enables server-side conversion tracking. Send conversion events directly from your server to LinkedIn, independent of browser-side tracking.

**Required scope:** `rw_conversions`

### 7.2 Setup: Create a Conversion Rule

```bash
curl -X POST "https://api.linkedin.com/rest/conversions" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "name": "Demo Request Completed",
    "account": "urn:li:sponsoredAccount:507404993",
    "conversionMethod": "CONVERSIONS_API",
    "postClickAttributionWindowSize": 30,
    "viewThroughAttributionWindowSize": 7,
    "attributionType": "LAST_TOUCH_BY_CAMPAIGN",
    "type": "LEAD"
  }'
```

### 7.3 Send Conversion Events

```bash
curl -X POST "https://api.linkedin.com/rest/conversionEvents" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  --data '{
    "conversion": "urn:lla:llaPartnerConversion:123456",
    "conversionHappenedAt": 1700000000000,
    "conversionValue": {
      "currencyCode": "USD",
      "amount": "500.00"
    },
    "eventId": "unique-event-id-12345",
    "user": {
      "userIds": [
        {
          "idType": "SHA256_EMAIL",
          "idValue": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
        }
      ],
      "userInfo": {
        "firstName": "John",
        "lastName": "Doe",
        "companyName": "Acme Corp",
        "title": "VP Marketing",
        "countryCode": "US"
      }
    }
  }'
```

```python
import hashlib
from datetime import datetime, timezone

def send_conversion_event(
    access_token: str,
    conversion_urn: str,
    email: str,
    event_id: str,
    value_usd: str = None,
    user_info: dict = None,
) -> dict:
    hashed_email = hashlib.sha256(
        email.lower().strip().encode("utf-8")
    ).hexdigest()

    body = {
        "conversion": conversion_urn,
        "conversionHappenedAt": int(datetime.now(timezone.utc).timestamp() * 1000),
        "eventId": event_id,  # for deduplication
        "user": {
            "userIds": [
                {"idType": "SHA256_EMAIL", "idValue": hashed_email}
            ],
        },
    }

    if value_usd:
        body["conversionValue"] = {"currencyCode": "USD", "amount": value_usd}
    if user_info:
        body["user"]["userInfo"] = user_info

    response = requests.post(
        "https://api.linkedin.com/rest/conversionEvents",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json=body,
    )
    response.raise_for_status()
    return response.json()
```

### 7.4 Event Types

| Type | Description |
|------|-------------|
| `LEAD` | Lead form submission, demo request |
| `PURCHASE` | Completed purchase |
| `ADD_TO_CART` | Added item to cart |
| `SIGN_UP` | Account creation |
| `DOWNLOAD` | Content/app download |
| `KEY_PAGE_VIEW` | High-value page visit |
| `INSTALL` | App installation |
| `OTHER` | Custom event |

### 7.5 Deduplication with Insight Tag

Use the `eventId` field for deduplication. If the same `eventId` is sent from both CAPI and the Insight Tag (browser pixel), LinkedIn deduplicates automatically. Best practice: generate a unique event ID client-side, pass it both to the pixel and to your server for CAPI.

### 7.6 Attribution Windows

| Setting | Options | Default |
|---------|---------|---------|
| `postClickAttributionWindowSize` | 1, 7, 30, 90 days | 30 |
| `viewThroughAttributionWindowSize` | 1, 7, 30, 90 days | 7 |
| `attributionType` | `LAST_TOUCH_BY_CAMPAIGN`, `LAST_TOUCH_BY_CONVERSION`, `EACH_CAMPAIGN` | `LAST_TOUCH_BY_CAMPAIGN` |

---

## 8. Reporting & Analytics

### 8.1 adAnalytics Endpoint

```
GET https://api.linkedin.com/rest/adAnalytics
```

**Required parameters:**

| Parameter | Description |
|-----------|-------------|
| `q` | Must be `analytics` |
| `pivot` | Dimension to group by |
| `dateRange.start` | `{year, month, day}` object |
| `dateRange.end` | `{year, month, day}` object |
| `timeGranularity` | `DAILY`, `MONTHLY`, or `ALL` |
| `accounts` or `campaigns` or `creatives` | URN(s) to filter by |

### 8.2 Full Example

```bash
curl -X GET "https://api.linkedin.com/rest/adAnalytics?q=analytics&pivot=CAMPAIGN&dateRange=(start:(year:2026,month:1,day:1),end:(year:2026,month:3,day:31))&timeGranularity=DAILY&accounts=List(urn%3Ali%3AsponsoredAccount%3A507404993)&fields=impressions,clicks,costInLocalCurrency,dateRange,pivotValue" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "LinkedIn-Version: 202603" \
  -H "X-Restli-Protocol-Version: 2.0.0"
```

```python
def get_campaign_analytics(
    access_token: str,
    account_id: int,
    start_date: dict,  # {"year": 2026, "month": 1, "day": 1}
    end_date: dict,
    pivot: str = "CAMPAIGN",
    fields: list[str] = None,
    granularity: str = "DAILY",
) -> list[dict]:
    default_fields = [
        "impressions", "clicks", "costInLocalCurrency",
        "dateRange", "pivotValue",
    ]
    response = requests.get(
        "https://api.linkedin.com/rest/adAnalytics",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202603",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        params={
            "q": "analytics",
            "pivot": pivot,
            "dateRange": f"(start:(year:{start_date['year']},month:{start_date['month']},day:{start_date['day']}),end:(year:{end_date['year']},month:{end_date['month']},day:{end_date['day']}))",
            "timeGranularity": granularity,
            "accounts": f"List(urn%3Ali%3AsponsoredAccount%3A{account_id})",
            "fields": ",".join(fields or default_fields),
        },
    )
    response.raise_for_status()
    return response.json().get("elements", [])
```

### 8.3 Available Metrics

| Metric | Description |
|--------|-------------|
| `impressions` | Total impressions |
| `clicks` | Total clicks (includes all click types) |
| `externalWebsiteConversions` | Total conversion events |
| `costInLocalCurrency` | Spend in account currency |
| `costInUsd` | Spend in USD |
| `likes` | Post likes |
| `comments` | Post comments |
| `shares` | Post shares |
| `follows` | Page follows from ad |
| `videoViews` | 2+ second video views |
| `videoCompletions` | Video views to 97%+ |
| `videoFirstQuartileCompletions` | 25% completion |
| `videoMidpointCompletions` | 50% completion |
| `videoThirdQuartileCompletions` | 75% completion |
| `leadGenerationMailContactInfoShares` | Lead gen form submissions |
| `textUrlClicks` | Clicks on the destination URL |
| `landingPageClicks` | Clicks to landing page |
| `oneClickLeads` | One-click lead gen submissions |
| `otherEngagements` | Other engagement actions |
| `totalEngagements` | Sum of all engagements |
| `conversionValueInLocalCurrency` | Total conversion value |
| `dateRange` | Date range for the data point |
| `pivotValue` | The entity URN for the pivot |

**Calculated metrics (compute client-side):**
- **CTR** = clicks / impressions
- **CPC** = costInLocalCurrency / clicks
- **CPM** = (costInLocalCurrency / impressions) * 1000
- **Engagement Rate** = totalEngagements / impressions

### 8.4 Pivot Dimensions

| Pivot | Groups by |
|-------|-----------|
| `CAMPAIGN` | Campaign URN |
| `CREATIVE` | Creative URN |
| `CAMPAIGN_GROUP` | Campaign group URN |
| `ACCOUNT` | Ad account URN |
| `COMPANY` | Company (for audience breakdown) |
| `MEMBER_COMPANY_SIZE` | Company size range |
| `MEMBER_INDUSTRY` | Member's industry |
| `MEMBER_SENIORITY` | Member's seniority |
| `MEMBER_JOB_TITLE` | Member's job title |
| `MEMBER_JOB_FUNCTION` | Member's job function |
| `MEMBER_COUNTRY_V2` | Member's country |
| `MEMBER_REGION_V2` | Member's region |

### 8.5 Date Range Handling

- `start` is inclusive, `end` is exclusive
- Maximum date range: 2 years (730 days) for DAILY granularity
- `timeGranularity: ALL` returns a single row aggregating the entire range
- Dates use `{year, month, day}` object format (not epoch timestamps)

### 8.6 Attribution Models

| Model | Description |
|-------|-------------|
| `LAST_TOUCH_BY_CAMPAIGN` | Credit goes to the last campaign that had an interaction |
| `LAST_TOUCH_BY_CONVERSION` | Credit goes to the last touchpoint before conversion |
| `EACH_CAMPAIGN` | Every campaign that had an interaction gets credit |

---

## 9. Rate Limits

### 9.1 Overview

LinkedIn enforces rate limits at two levels simultaneously:

| Limit Type | What It Controls |
|---|---|
| **Application-level** | Total calls your app can make per day across all members |
| **Member-level** | Total calls a single member's token can make per day via your app |

Limits reset at **midnight UTC** daily.

### 9.2 Finding Your Actual Limits

LinkedIn does **not publish standard per-endpoint rate limits**. Limits vary by endpoint, app tier, and internal allocation. To check:

1. Make at least one test call to the endpoint
2. Go to [Developer Portal](https://www.linkedin.com/developers/apps) > My Apps > Analytics tab
3. View usage and allocated limits per endpoint

**DMP Segment streaming endpoints** have explicit per-minute limits:

| Endpoint | Per-Minute Limit |
|---|---|
| `POST /dmpSegments/{id}/users` | 600 requests/minute |
| `POST /dmpSegments/{id}/companies` | 300 requests/minute |

### 9.3 Throttling Behavior

Rate-limited requests return **HTTP 429 Too Many Requests**:

```json
{
  "serviceErrorCode": 101,
  "message": "Resource level throttle APPLICATION_AND_MEMBER DAY limit for calls to this resource is reached",
  "status": 429
}
```

LinkedIn does **not** document guaranteed `X-RateLimit-*` or `Retry-After` headers.

### 9.4 Retry Strategy

```python
import time

def call_with_retry(client, url, headers, params, max_retries=5):
    delay = 2
    for attempt in range(max_retries):
        response = client.get(url, headers=headers, params=params)
        if response.status_code == 429:
            if attempt == max_retries - 1:
                raise Exception(f"Rate limit exceeded after {max_retries} attempts")
            time.sleep(delay)
            delay = min(delay * 2, 300)  # cap at 5 minutes
            continue
        response.raise_for_status()
        return response
```

### 9.5 Rate Limit Alerts

LinkedIn sends email alerts to Developer Admin users when an app exceeds **75% of its daily quota** for an endpoint. Alerts have a 1–2 hour delivery delay.

### 9.6 Best Practices

- Cache read responses aggressively
- Use batch endpoints (`BATCH_GET`, `BATCH_PARTIAL_UPDATE`) to minimize call count
- Spread DMP uploads over time rather than bursting
- Monitor the Developer Portal Analytics tab proactively

---

## 10. Python Libraries

### 10.1 Official LinkedIn Python Client

LinkedIn provides an official Python client: **`linkedin-api-client`** (beta).

```bash
pip install linkedin-api-client
```

- **GitHub:** `linkedin-developers/linkedin-api-python-client`
- **What it does:** Handles Rest.li protocol complexity (encoding, query tunneling, headers)
- **What it doesn't do:** No Marketing-API-specific methods — you still construct all calls

**Auth client:**

```python
from linkedin_api.clients.auth.client import AuthClient

auth_client = AuthClient(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    redirect_url="YOUR_REDIRECT_URL"
)

auth_url = auth_client.generate_member_auth_url(
    scopes=["r_ads", "rw_ads", "r_ads_reporting"]
)

token_response = auth_client.exchange_auth_code_for_access_token(code="AUTH_CODE")
access_token = token_response.access_token
```

**Rest.li client:**

```python
from linkedin_api.clients.restli.client import RestliClient

client = RestliClient()

# Finder (search campaigns)
response = client.finder(
    resource_path="/adCampaigns",
    finder_name="search",
    query_params={"search": {"status": {"values": ["ACTIVE"]}}},
    access_token=access_token,
    version_string="202603",
)
```

### 10.2 Community Libraries

| Library | Status | Notes |
|---|---|---|
| `linkedin-api-client` | Official, beta | **Recommended** |
| `linkedin-api` (Tom Quirk) | Unofficial scraper | **Violates ToS** — do not use for production |
| `python3-linkedin` | Stale | Outdated |

### 10.3 Clean Client Pattern (Raw HTTP)

```python
import time
import requests

LINKEDIN_VERSION = "202603"


class LinkedInMarketingClient:
    def __init__(self, access_token: str, version: str = LINKEDIN_VERSION):
        self.access_token = access_token
        self.version = version
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, url: str, **kwargs) -> dict:
        delay = 2
        for attempt in range(5):
            response = self.session.request(method, url, **kwargs)
            if response.status_code == 429:
                if attempt == 4:
                    response.raise_for_status()
                time.sleep(delay)
                delay = min(delay * 2, 300)
                continue
            response.raise_for_status()
            return response.json() if response.content else {}
        return {}

    def get_ad_accounts(self, status: str = "ACTIVE") -> list[dict]:
        return self._request(
            "GET",
            "https://api.linkedin.com/rest/adAccounts",
            params={"q": "search", "search": f"(status:(values:List({status})))"},
        ).get("elements", [])

    def get_campaigns(self, account_id: int,
                      statuses: list[str] = None) -> list[dict]:
        status_list = ",".join(statuses or ["ACTIVE"])
        return self._request(
            "GET",
            f"https://api.linkedin.com/rest/adAccounts/{account_id}/adCampaigns",
            params={
                "q": "search",
                "search": f"(status:(values:List({status_list})))",
            },
        ).get("elements", [])

    def get_analytics(self, account_id: int, start: dict,
                      end: dict, pivot: str = "CAMPAIGN") -> list[dict]:
        date_range = (
            f"(start:(year:{start['year']},month:{start['month']},day:{start['day']}),"
            f"end:(year:{end['year']},month:{end['month']},day:{end['day']}))"
        )
        return self._request(
            "GET",
            "https://api.linkedin.com/rest/adAnalytics",
            params={
                "q": "analytics",
                "pivot": pivot,
                "dateRange": date_range,
                "timeGranularity": "DAILY",
                "accounts": f"List(urn%3Ali%3AsponsoredAccount%3A{account_id})",
                "fields": "impressions,clicks,costInLocalCurrency,dateRange,pivotValue",
            },
        ).get("elements", [])
```

---

## 11. Common Gotchas

### 11.1 API Approval Timeline

| Product | Access Type | Timeline |
|---|---|---|
| Advertising API (Dev tier) | Self-serve | Near-immediate |
| Advertising API (Standard tier) | Support ticket + video demo | Weeks to months |
| Matched Audiences / `rw_dmp_segments` | Private program; interest form | Up to **60 days**; no guarantee |
| Lead Sync API | Self-serve with prerequisites | Days |
| Conversions API | Self-serve with prerequisites | Days |

**Standard tier requires a video demonstration.** Text descriptions are not sufficient. LinkedIn reserves the right to deny upgrades even if minimum requirements are met.

**Company Page association required:** Your developer app must be associated with a LinkedIn Company Page (super admin must approve). Without this, organization-related calls silently fail or return 403.

### 11.2 Things That Silently Fail

- **Empty 200 from adAnalytics:** No data OR no permission both return `HTTP 200` with empty `elements` array — indistinguishable
- **Zero `unitCost` with manual bidding:** Campaign is accepted (201) but never delivers impressions
- **Audience upload with 0 matches:** Returns 200, segment shows READY, but audience count is 0
- **DMP segment stuck in BUILDING:** Streaming to an archived segment transitions it back to BUILDING

### 11.3 Undocumented / Easily-Missed Required Fields

- **`interfaceLocales` in targeting:** Must be included in `targetingCriteria.include` on PATCH updates
- **`offsiteDeliveryEnabled`:** No default — must be explicitly set
- **`campaignGroup`:** Required since October 30, 2020
- **`politicalIntent`:** Required for EU-targeted campaigns (since October 10, 2025) — values: `POLITICAL`, `NOT_POLITICAL`, `NOT_DECLARED`
- **Email hashing:** Must lowercase and strip whitespace BEFORE hashing. Wrong order = 200 response, 0 matches

### 11.4 Creative Review Delays

- Review is **human-performed**, typically 24 hours, up to 48 hours
- Campaign shows as running but may not deliver during review
- Rejected creatives **cannot be edited** — must create new ones
- A campaign with only FAILED creatives blocks new creative creation (`CREATE_NOT_ALLOWED_WITH_FAILED_CREATIVES`) — archive failed ones first

### 11.5 Targeting Restrictions

| Restriction | Detail |
|---|---|
| `offsiteDeliveryEnabled: true` | Blocked for Lead Generation campaigns |
| Text Ads | Cannot use LinkedIn Audience Network |
| CTV campaigns | US/Canada only, BRAND_AWARENESS, SINGLE_VIDEO, no manual bidding |
| Location facet mixing | `locations` and `profileLocations` cannot both be in same targeting |
| Predictive Audiences | Requires geo filter; no other facets supported |
| Audience size minimum | 300 matched members required |

### 11.6 Audience Upload Failures

| Cause | Symptom | Fix |
|---|---|---|
| Emails not lowercased before hashing | 200, 0 matches | Lowercase before SHA256 |
| SHA512 used for CSV upload | 200, 0 matches | CSV accepts SHA256 only |
| Audience < 300 matched | `AUDIENCE_SIZE_TOO_SMALL` | Upload more data |
| Members opted out | Matched > 0, served = 0 | Cannot resolve (privacy) |
| Segment expired (90 days) | 400 on campaign add | Re-upload; segment purged |
| `rw_dmp_segments` not granted | 403 | Apply for Matched Audiences program |

### 11.7 API Versioning

Every request requires `LinkedIn-Version: YYYYMM`. Missing header returns 400. Deprecated version returns **HTTP 426** (Upgrade Required).

- Versions supported for minimum **1 year** from release
- Monthly releases since January 2022
- Migration is simple: bump the header value

```json
// Missing version header
{"status": 400, "code": "VERSION_MISSING", "message": "A version must be present..."}

// Deprecated version
{"status": 426, "code": "NONEXISTENT_VERSION", "message": "Requested version is not active"}
```

### 11.8 Key Error Codes

| Code | HTTP | Meaning |
|---|---|---|
| `VERSION_MISSING` | 400 | No `LinkedIn-Version` header |
| `NONEXISTENT_VERSION` | 426 | Version is sunset |
| `MISSING_FIELD` | 400 | Required field omitted |
| `FIELD_VALUE_TOO_LOW` | 400 | Value below minimum (e.g., budget) |
| `IMMUTABLE_CAMPAIGN_OBJECTIVE_TYPE` | 400 | Can't change objective after creation |
| `AUDIENCE_SIZE_TOO_SMALL` | 400 | < 300 matched members |
| `CREATE_NOT_ALLOWED_WITH_FAILED_CREATIVES` | 400 | Archive failed creatives first |
| `STATUS_CHANGE_NOT_ALLOWED` | 400 | Invalid status transition |
| `NO_PERMISSION_ON_ENTITY` | 403 | Token lacks permission |
| `INCOMPATIBLE_TARGETING_COMBINATION` | 400 | Facets can't be combined |
| `MULTIPLE_VALIDATIONS_FAILED` | 400 | Check `errorDetails` |

**Batch operations:** 200 HTTP status does NOT mean all entities succeeded. Always check both `results` and `errors` keys.

---

## Sources

All information sourced from official LinkedIn documentation:
- [LinkedIn Marketing API](https://learn.microsoft.com/en-us/linkedin/marketing/)
- [LinkedIn Shared Authentication](https://learn.microsoft.com/en-us/linkedin/shared/authentication/)
- [LinkedIn API Error Handling](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/error-handling)
- [LinkedIn API Rate Limits](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits)
- [LinkedIn Marketing API Versioning](https://learn.microsoft.com/en-us/linkedin/marketing/versioning)
- [Official Python Client](https://github.com/linkedin-developers/linkedin-api-python-client)
