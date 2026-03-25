"""Asset generation endpoints.

Separate router from the rendering router — handles AI-powered content
generation, revision, approval, and listing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client as SupabaseClient

from app.assets.service import AssetGenerationService
from app.auth.models import UserProfile
from app.dependencies import get_claude, get_current_user, get_supabase, get_tenant
from app.integrations.claude_ai import ClaudeClient
from app.tenants.models import Organization

router = APIRouter(prefix="/assets", tags=["asset-generation"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    campaign_id: str
    asset_types: list[str]
    platforms: list[str] | None = None
    angle: str | None = None
    tone: str | None = None
    cta: str | None = None
    # Per-type config
    lead_magnet_format: str | None = None
    landing_page_template: str | None = None
    document_ad_pattern: str | None = None
    video_duration: str | None = None
    email_trigger: str | None = None


class GeneratedAssetResponse(BaseModel):
    id: str
    asset_type: str
    status: str
    content_url: str | None = None
    content_preview: dict | None = None
    template_used: str | None = None
    error: str | None = None


class ReviseRequest(BaseModel):
    revision_instructions: str


class AssetDetailResponse(BaseModel):
    id: str
    asset_type: str
    status: str
    content_url: str | None = None
    content_json: dict | None = None
    template_used: str | None = None
    campaign_id: str | None = None
    organization_id: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Service factory
# ---------------------------------------------------------------------------


def _get_service(
    claude: ClaudeClient = Depends(get_claude),
    supabase: SupabaseClient = Depends(get_supabase),
) -> AssetGenerationService:
    return AssetGenerationService(claude=claude, supabase=supabase)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=list[GeneratedAssetResponse])
async def generate_assets(
    body: GenerateRequest,
    user: UserProfile = Depends(get_current_user),
    tenant: Organization = Depends(get_tenant),
    service: AssetGenerationService = Depends(_get_service),
):
    """Generate one or more assets for a campaign."""
    results = await service.generate(
        org_id=str(tenant.id),
        campaign_id=body.campaign_id,
        asset_types=body.asset_types,
        platforms=body.platforms,
        angle=body.angle,
        tone=body.tone,
        cta=body.cta,
        lead_magnet_format=body.lead_magnet_format,
        landing_page_template=body.landing_page_template,
        document_ad_pattern=body.document_ad_pattern,
        video_duration=body.video_duration,
        email_trigger=body.email_trigger,
    )
    return results


@router.get("/{asset_id}", response_model=AssetDetailResponse)
async def get_asset(
    asset_id: str,
    user: UserProfile = Depends(get_current_user),
    tenant: Organization = Depends(get_tenant),
    service: AssetGenerationService = Depends(_get_service),
):
    """Get full asset detail."""
    return service.get_asset(asset_id, str(tenant.id))


@router.patch("/{asset_id}", response_model=GeneratedAssetResponse)
async def revise_asset(
    asset_id: str,
    body: ReviseRequest,
    user: UserProfile = Depends(get_current_user),
    tenant: Organization = Depends(get_tenant),
    service: AssetGenerationService = Depends(_get_service),
):
    """Revise an asset with new instructions (re-generates content)."""
    return await service.revise_asset(
        asset_id=asset_id,
        revision_instructions=body.revision_instructions,
        org_id=str(tenant.id),
    )


@router.post("/{asset_id}/approve", response_model=AssetDetailResponse)
async def approve_asset(
    asset_id: str,
    user: UserProfile = Depends(get_current_user),
    tenant: Organization = Depends(get_tenant),
    service: AssetGenerationService = Depends(_get_service),
):
    """Approve a draft asset (draft → approved)."""
    return service.approve_asset(asset_id, str(tenant.id))


@router.get("/campaigns/{campaign_id}/assets", response_model=list[AssetDetailResponse])
async def list_campaign_assets(
    campaign_id: str,
    user: UserProfile = Depends(get_current_user),
    tenant: Organization = Depends(get_tenant),
    service: AssetGenerationService = Depends(_get_service),
):
    """List all assets for a campaign."""
    return service.list_campaign_assets(campaign_id, str(tenant.id))
