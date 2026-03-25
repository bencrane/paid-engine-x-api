"""Tests for the asset generation orchestrator (service + router)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from app.assets.context import AssetContext
from app.assets.service import (
    VALID_ASSET_TYPES,
    AssetGenerationService,
    _build_preview,
)
from app.shared.errors import BadRequestError, NotFoundError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _ctx(**overrides: Any) -> AssetContext:
    defaults = dict(
        organization_id="org-1",
        company_name="TestCo",
        brand_voice="Professional",
        value_proposition="We simplify X",
        target_persona="CISOs at mid-market companies",
        angle="Security compliance",
        objective="lead_gen",
        platforms=["linkedin"],
        industry="SaaS",
        case_studies=[{"customer_name": "BigCo", "results": {"roi": "3x"}}],
        testimonials=[{"quote": "Great", "author": "J", "title": "CTO", "company": "X"}],
    )
    defaults.update(overrides)
    return AssetContext(**defaults)


class _FakeOutput(BaseModel):
    title: str = "Test"
    body: str = "Test body content"


def _mock_supabase() -> MagicMock:
    """Create a Supabase mock with chained query builder pattern."""
    mock = MagicMock()

    # The chained builder pattern: table().select().eq().eq().maybe_single().execute()
    # and table().insert().execute(), table().update().eq().execute(), etc.
    def _make_chain(data=None):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        chain.order.return_value = chain
        chain.range.return_value = chain
        res = MagicMock()
        res.data = data
        res.count = len(data) if data else 0
        chain.execute.return_value = res
        return chain

    # Default: return empty data
    mock.table.return_value = _make_chain([])

    return mock


def _mock_supabase_with_asset(asset_data: dict) -> MagicMock:
    """Supabase mock that returns specific asset data on select."""
    mock = MagicMock()

    def _table(name: str):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        chain.order.return_value = chain

        if name == "generated_assets":
            res = MagicMock()
            res.data = asset_data
            chain.execute.return_value = res
        else:
            res = MagicMock()
            res.data = []
            chain.execute.return_value = res
        return chain

    mock.table.side_effect = _table
    return mock


def _mock_claude() -> MagicMock:
    mock = MagicMock()
    mock.generate_structured = AsyncMock(return_value=_FakeOutput())
    return mock


# ---------------------------------------------------------------------------
# Service: generate() tests
# ---------------------------------------------------------------------------


class TestServiceGenerate:
    @pytest.mark.asyncio
    @patch("app.assets.service.build_asset_context", new_callable=AsyncMock)
    @patch("app.assets.service.generate_email_sequence", new_callable=AsyncMock)
    async def test_single_text_asset_generation(
        self, mock_gen_email, mock_build_ctx
    ):
        """Single text-only asset type completes with status=draft."""
        mock_build_ctx.return_value = _ctx()
        from app.assets.prompts.schemas import EmailSequenceOutput, NurtureEmail

        mock_gen_email.return_value = EmailSequenceOutput(
            sequence_name="Test",
            trigger="lead_magnet_download",
            emails=[
                NurtureEmail(
                    subject_line="Welcome",
                    preview_text="Thanks for downloading",
                    body_html="<p>Hi</p>",
                    send_delay_days=0,
                    purpose="value_delivery",
                ),
                NurtureEmail(
                    subject_line="Tip #1",
                    preview_text="Here's a tip",
                    body_html="<p>Tip</p>",
                    send_delay_days=2,
                    purpose="education",
                ),
                NurtureEmail(
                    subject_line="See results",
                    preview_text="Others saw this",
                    body_html="<p>Proof</p>",
                    send_delay_days=5,
                    purpose="social_proof",
                ),
            ],
        )

        supabase = _mock_supabase()
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        results = await service.generate(
            org_id="org-1",
            campaign_id="camp-1",
            asset_types=["email_copy"],
        )

        assert len(results) == 1
        assert results[0]["asset_type"] == "email_copy"
        assert results[0]["status"] == "draft"
        assert results[0]["error"] is None
        assert results[0]["content_preview"] is not None

    @pytest.mark.asyncio
    @patch("app.assets.service.build_asset_context", new_callable=AsyncMock)
    @patch("app.assets.service.generate_ad_copy", new_callable=AsyncMock)
    @patch("app.assets.service.generate_email_sequence", new_callable=AsyncMock)
    async def test_multi_type_parallel_generation(
        self, mock_gen_email, mock_gen_ad, mock_build_ctx
    ):
        """Multiple asset types generate in parallel."""
        mock_build_ctx.return_value = _ctx()
        mock_gen_ad.return_value = {"linkedin": _FakeOutput()}
        from app.assets.prompts.schemas import EmailSequenceOutput, NurtureEmail

        mock_gen_email.return_value = EmailSequenceOutput(
            sequence_name="Test",
            trigger="lead_magnet_download",
            emails=[
                NurtureEmail(
                    subject_line="Welcome",
                    preview_text="Thanks",
                    body_html="<p>Hi</p>",
                    send_delay_days=0,
                    purpose="value_delivery",
                ),
                NurtureEmail(
                    subject_line="Tip",
                    preview_text="Here",
                    body_html="<p>T</p>",
                    send_delay_days=2,
                    purpose="education",
                ),
                NurtureEmail(
                    subject_line="See",
                    preview_text="Others",
                    body_html="<p>P</p>",
                    send_delay_days=5,
                    purpose="social_proof",
                ),
            ],
        )

        supabase = _mock_supabase()
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        results = await service.generate(
            org_id="org-1",
            campaign_id="camp-1",
            asset_types=["ad_copy", "email_copy"],
            platforms=["linkedin"],
        )

        assert len(results) == 2
        types = {r["asset_type"] for r in results}
        assert types == {"ad_copy", "email_copy"}

    @pytest.mark.asyncio
    @patch("app.assets.service.build_asset_context", new_callable=AsyncMock)
    @patch("app.assets.service.generate_ad_copy", new_callable=AsyncMock)
    @patch("app.assets.service.generate_email_sequence", new_callable=AsyncMock)
    async def test_failed_generation_does_not_block_others(
        self, mock_gen_email, mock_gen_ad, mock_build_ctx
    ):
        """If one asset type fails, others still complete."""
        mock_build_ctx.return_value = _ctx()
        mock_gen_ad.side_effect = RuntimeError("Claude API error")
        from app.assets.prompts.schemas import EmailSequenceOutput, NurtureEmail

        mock_gen_email.return_value = EmailSequenceOutput(
            sequence_name="Test",
            trigger="lead_magnet_download",
            emails=[
                NurtureEmail(
                    subject_line="W",
                    preview_text="T",
                    body_html="<p>H</p>",
                    send_delay_days=0,
                    purpose="value_delivery",
                ),
                NurtureEmail(
                    subject_line="T",
                    preview_text="H",
                    body_html="<p>T</p>",
                    send_delay_days=2,
                    purpose="education",
                ),
                NurtureEmail(
                    subject_line="S",
                    preview_text="O",
                    body_html="<p>P</p>",
                    send_delay_days=5,
                    purpose="social_proof",
                ),
            ],
        )

        supabase = _mock_supabase()
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        results = await service.generate(
            org_id="org-1",
            campaign_id="camp-1",
            asset_types=["ad_copy", "email_copy"],
            platforms=["linkedin"],
        )

        assert len(results) == 2
        statuses = {r["asset_type"]: r["status"] for r in results}
        assert statuses["ad_copy"] == "failed"
        assert statuses["email_copy"] == "draft"
        # Failed result has error message
        failed = [r for r in results if r["asset_type"] == "ad_copy"][0]
        assert failed["error"] is not None
        assert "Claude API error" in failed["error"]

    @pytest.mark.asyncio
    async def test_invalid_asset_type_raises(self):
        """Unknown asset type raises BadRequestError."""
        supabase = _mock_supabase()
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        with pytest.raises(BadRequestError, match="Unknown asset type"):
            await service.generate(
                org_id="org-1",
                campaign_id="camp-1",
                asset_types=["nonexistent"],
            )

    @pytest.mark.asyncio
    @patch("app.assets.service.build_asset_context", new_callable=AsyncMock)
    @patch("app.assets.service.generate_video_script", new_callable=AsyncMock)
    async def test_context_overrides_applied(
        self, mock_gen_video, mock_build_ctx
    ):
        """Angle, tone, and platform overrides are applied to context."""
        ctx = _ctx()
        mock_build_ctx.return_value = ctx
        from app.assets.prompts.schemas import ScriptSegment, VideoScriptOutput

        seg = ScriptSegment(
            timestamp_start="0:00",
            timestamp_end="0:03",
            spoken_text="Hi",
            visual_direction="Close up",
            caption_text="Hi",
        )
        mock_gen_video.return_value = VideoScriptOutput(
            title="T",
            duration="30s",
            aspect_ratio="4:5",
            hook=seg,
            body=[seg],
            cta=seg,
            total_word_count=50,
            music_direction="Upbeat",
            target_platform="linkedin",
        )

        supabase = _mock_supabase()
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        await service.generate(
            org_id="org-1",
            campaign_id="camp-1",
            asset_types=["video_script"],
            angle="New angle",
            tone="Casual and fun",
            platforms=["meta"],
        )

        # Overrides should be applied to context
        assert ctx.angle == "New angle"
        assert ctx.brand_voice == "Casual and fun"
        assert ctx.platforms == ["meta"]


# ---------------------------------------------------------------------------
# Service: revise_asset() tests
# ---------------------------------------------------------------------------


class TestServiceRevise:
    @pytest.mark.asyncio
    @patch("app.assets.service.build_asset_context", new_callable=AsyncMock)
    @patch("app.assets.service.generate_email_sequence", new_callable=AsyncMock)
    async def test_revision_flow(self, mock_gen_email, mock_build_ctx):
        """Revision re-generates asset and updates row."""
        mock_build_ctx.return_value = _ctx()
        from app.assets.prompts.schemas import EmailSequenceOutput, NurtureEmail

        mock_gen_email.return_value = EmailSequenceOutput(
            sequence_name="Revised",
            trigger="lead_magnet_download",
            emails=[
                NurtureEmail(
                    subject_line="New",
                    preview_text="Rev",
                    body_html="<p>R</p>",
                    send_delay_days=0,
                    purpose="value_delivery",
                ),
                NurtureEmail(
                    subject_line="New2",
                    preview_text="Rev2",
                    body_html="<p>R2</p>",
                    send_delay_days=2,
                    purpose="education",
                ),
                NurtureEmail(
                    subject_line="New3",
                    preview_text="Rev3",
                    body_html="<p>R3</p>",
                    send_delay_days=5,
                    purpose="social_proof",
                ),
            ],
        )

        asset_data = {
            "id": "asset-1",
            "asset_type": "email_copy",
            "status": "draft",
            "organization_id": "org-1",
            "campaign_id": "camp-1",
        }
        supabase = _mock_supabase_with_asset(asset_data)
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        result = await service.revise_asset(
            asset_id="asset-1",
            revision_instructions="Make it more casual",
            org_id="org-1",
        )

        assert result["id"] == "asset-1"
        assert result["status"] == "draft"
        assert result["asset_type"] == "email_copy"

    @pytest.mark.asyncio
    async def test_revision_not_found_raises(self):
        """Revising a non-existent asset raises 404."""
        supabase = _mock_supabase_with_asset(None)
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        with pytest.raises(NotFoundError, match="Asset not found"):
            await service.revise_asset(
                asset_id="nonexistent",
                revision_instructions="Make it better",
                org_id="org-1",
            )


# ---------------------------------------------------------------------------
# Service: approve_asset() tests
# ---------------------------------------------------------------------------


class TestServiceApprove:
    def test_approve_draft_asset(self):
        """Draft → approved transition succeeds."""
        asset_data = {
            "id": "asset-1",
            "asset_type": "ad_copy",
            "status": "draft",
            "organization_id": "org-1",
            "content_url": None,
        }
        supabase = _mock_supabase_with_asset(asset_data)
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        result = service.approve_asset("asset-1", "org-1")
        assert result["status"] == "approved"

    def test_approve_non_draft_raises(self):
        """Approving a non-draft asset raises error."""
        asset_data = {
            "id": "asset-1",
            "asset_type": "ad_copy",
            "status": "approved",
            "organization_id": "org-1",
        }
        supabase = _mock_supabase_with_asset(asset_data)
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        with pytest.raises(BadRequestError, match="Can only approve draft"):
            service.approve_asset("asset-1", "org-1")

    def test_approve_not_found_raises(self):
        """Approving non-existent asset raises 404."""
        supabase = _mock_supabase_with_asset(None)
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        with pytest.raises(NotFoundError):
            service.approve_asset("nonexistent", "org-1")


# ---------------------------------------------------------------------------
# Service: get_asset() / list_campaign_assets() tests
# ---------------------------------------------------------------------------


class TestServiceRead:
    def test_get_asset_returns_data(self):
        """get_asset returns full row."""
        asset_data = {
            "id": "asset-1",
            "asset_type": "email_copy",
            "status": "draft",
            "organization_id": "org-1",
        }
        supabase = _mock_supabase_with_asset(asset_data)
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        result = service.get_asset("asset-1", "org-1")
        assert result["id"] == "asset-1"

    def test_get_asset_not_found(self):
        supabase = _mock_supabase_with_asset(None)
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        with pytest.raises(NotFoundError):
            service.get_asset("nonexistent", "org-1")

    def test_list_campaign_assets(self):
        """list_campaign_assets returns list of assets."""
        mock = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        res = MagicMock()
        res.data = [
            {"id": "a1", "asset_type": "ad_copy", "status": "draft"},
            {"id": "a2", "asset_type": "email_copy", "status": "draft"},
        ]
        chain.execute.return_value = res
        mock.table.return_value = chain

        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=mock)
        result = service.list_campaign_assets("camp-1", "org-1")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Service: dispatch tests
# ---------------------------------------------------------------------------


class TestDispatch:
    @pytest.mark.asyncio
    @patch("app.assets.service.build_asset_context", new_callable=AsyncMock)
    @patch("app.assets.service.generate_image_briefs", new_callable=AsyncMock)
    async def test_image_brief_dispatch(self, mock_gen, mock_build_ctx):
        """image_brief dispatches to generate_image_briefs."""
        mock_build_ctx.return_value = _ctx()
        from app.assets.prompts.schemas import ImageBriefOutput, ImageBriefSetOutput

        mock_gen.return_value = ImageBriefSetOutput(
            briefs=[
                ImageBriefOutput(
                    concept_name="C1",
                    intended_use="linkedin_sponsored",
                    dimensions="1200x628",
                    visual_description="Overhead shot",
                    mood="confident",
                    style_reference="Apple",
                )
            ]
        )

        supabase = _mock_supabase()
        claude = _mock_claude()
        service = AssetGenerationService(claude=claude, supabase=supabase)

        results = await service.generate(
            org_id="org-1",
            campaign_id="camp-1",
            asset_types=["image_brief"],
        )

        assert len(results) == 1
        assert results[0]["asset_type"] == "image_brief"
        assert results[0]["status"] == "draft"
        mock_gen.assert_called_once()


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


class TestRequestValidation:
    def test_generate_request_model(self):
        """GenerateRequest validates required fields."""
        from app.assets.generation_router import GenerateRequest

        req = GenerateRequest(
            campaign_id="camp-1",
            asset_types=["ad_copy", "email_copy"],
            platforms=["linkedin"],
        )
        assert req.campaign_id == "camp-1"
        assert len(req.asset_types) == 2

    def test_generate_request_optional_fields(self):
        """Optional per-type config fields default to None."""
        from app.assets.generation_router import GenerateRequest

        req = GenerateRequest(
            campaign_id="camp-1",
            asset_types=["lead_magnet"],
        )
        assert req.lead_magnet_format is None
        assert req.landing_page_template is None
        assert req.platforms is None

    def test_revise_request_model(self):
        from app.assets.generation_router import ReviseRequest

        req = ReviseRequest(revision_instructions="Make it shorter")
        assert req.revision_instructions == "Make it shorter"


# ---------------------------------------------------------------------------
# Preview helper
# ---------------------------------------------------------------------------


class TestBuildPreview:
    def test_dict_preview(self):
        result = _build_preview({"key": "value"})
        assert result["type"] == "json"
        assert "key" in result["summary"]

    def test_long_preview_truncated(self):
        data = {"long": "x" * 1000}
        result = _build_preview(data, max_chars=100)
        assert len(result["summary"]) <= 100


# ---------------------------------------------------------------------------
# Valid asset types constant
# ---------------------------------------------------------------------------


class TestConstants:
    def test_valid_asset_types(self):
        expected = {
            "lead_magnet", "landing_page", "document_ad", "case_study_page",
            "ad_copy", "email_copy", "video_script", "image_brief",
        }
        assert VALID_ASSET_TYPES == expected
