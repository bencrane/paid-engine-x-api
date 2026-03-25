"""Tests for BJC-173: Image concept brief content generator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assets.context import AssetContext
from app.assets.generators.image_brief import (
    PLATFORM_DIMENSIONS,
    VALID_PLATFORMS,
    ImageBriefGenerator,
    generate_image_briefs,
)
from app.assets.prompts.schemas import ImageBriefOutput, ImageBriefSetOutput


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _ctx(**overrides: Any) -> AssetContext:
    defaults = dict(
        organization_id="org-1",
        company_name="TestCo",
        brand_voice="Professional and clear",
        value_proposition="We simplify compliance",
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


def _brief_set_output(n: int = 1) -> ImageBriefSetOutput:
    briefs = [
        ImageBriefOutput(
            concept_name=f"Concept {i+1}",
            intended_use=f"linkedin_sponsored",
            dimensions="1200x628",
            visual_description=(
                "Overhead shot of four people around a whiteboard covered in sticky "
                "notes, warm natural light from a floor-to-ceiling window on the left"
            ),
            text_overlay="Simplify Compliance Today",
            color_palette=["#1A73E8", "#34A853", "#FFFFFF"],
            mood="confident and forward-looking",
            style_reference="Apple product photography",
            do_not_include=["handshake photos", "generic office scenes"],
        )
        for i in range(n)
    ]
    return ImageBriefSetOutput(briefs=briefs)


def _mock_claude(return_value: Any = None) -> MagicMock:
    mock = MagicMock()
    mock.generate_structured = AsyncMock(
        return_value=return_value or _brief_set_output()
    )
    return mock


# ---------------------------------------------------------------------------
# Platform dimension tests
# ---------------------------------------------------------------------------


class TestPlatformDimensions:
    def _get_instructions(self, platforms: list[str] | None = None) -> str:
        gen = ImageBriefGenerator()
        return gen.build_asset_specific_instructions(
            _ctx(), platforms=platforms or ["linkedin_sponsored"]
        )

    def test_linkedin_sponsored_dimensions(self):
        text = self._get_instructions(["linkedin_sponsored"])
        assert "1200x628" in text
        assert "LinkedIn Sponsored" in text

    def test_linkedin_carousel_dimensions(self):
        text = self._get_instructions(["linkedin_carousel"])
        assert "1080x1080" in text
        assert "Carousel" in text

    def test_meta_feed_dimensions(self):
        text = self._get_instructions(["meta_feed"])
        assert "1080x1080" in text
        assert "Meta Feed" in text

    def test_meta_story_dimensions(self):
        text = self._get_instructions(["meta_story"])
        assert "1080x1920" in text
        assert "9:16" in text

    def test_landing_page_hero_dimensions(self):
        text = self._get_instructions(["landing_page_hero"])
        assert "1920x1080" in text
        assert "16:9" in text

    def test_multiple_platforms_in_prompt(self):
        text = self._get_instructions(["linkedin_sponsored", "meta_feed"])
        assert "1200x628" in text
        assert "1080x1080" in text

    def test_unknown_platform_raises(self):
        gen = ImageBriefGenerator()
        with pytest.raises(ValueError, match="Unknown image platform"):
            gen.build_asset_specific_instructions(_ctx(), platforms=["tiktok"])

    def test_default_platform_is_linkedin_sponsored(self):
        gen = ImageBriefGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "LinkedIn Sponsored" in text


# ---------------------------------------------------------------------------
# Brand color guidance
# ---------------------------------------------------------------------------


class TestBrandColors:
    def test_brand_guidelines_injected(self):
        ctx = _ctx(brand_guidelines={"colors": "#1A73E8, #34A853", "tone": "Bold and modern"})
        gen = ImageBriefGenerator()
        text = gen.build_asset_specific_instructions(ctx, platforms=["linkedin_sponsored"])
        assert "#1A73E8" in text
        assert "hex" in text.lower()

    def test_no_brand_guidelines_fallback(self):
        ctx = _ctx()
        gen = ImageBriefGenerator()
        text = gen.build_asset_specific_instructions(ctx, platforms=["linkedin_sponsored"])
        assert "cohesive" in text.lower() or "professional" in text.lower()


# ---------------------------------------------------------------------------
# Visual description quality rules
# ---------------------------------------------------------------------------


class TestVisualDescriptionRules:
    def test_contains_specificity_guidance(self):
        gen = ImageBriefGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), platforms=["linkedin_sponsored"])
        assert "SPECIFIC" in text or "specific" in text.lower()
        assert "BAD" in text
        assert "GOOD" in text

    def test_contains_photography_terms(self):
        gen = ImageBriefGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), platforms=["linkedin_sponsored"])
        assert "camera angle" in text.lower() or "lighting" in text.lower()
        assert "depth of field" in text.lower()


# ---------------------------------------------------------------------------
# Anti-cliché / do_not_include
# ---------------------------------------------------------------------------


class TestAntiCliche:
    def test_contains_do_not_include_guidance(self):
        gen = ImageBriefGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), platforms=["linkedin_sponsored"])
        assert "do_not_include" in text.lower() or "DO NOT INCLUDE" in text
        assert "handshake" in text.lower()
        assert "puzzle" in text.lower() or "gears" in text.lower()


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


class TestGenerateImageBriefs:
    @pytest.mark.asyncio
    async def test_returns_image_brief_set_output(self):
        mock = _mock_claude()
        result = await generate_image_briefs(mock, _ctx())
        assert isinstance(result, ImageBriefSetOutput)
        assert len(result.briefs) >= 1

    @pytest.mark.asyncio
    async def test_passes_platforms_to_generator(self):
        mock = _mock_claude(_brief_set_output(2))
        result = await generate_image_briefs(
            mock, _ctx(), platforms=["linkedin_sponsored", "meta_feed"]
        )
        call_kwargs = mock.generate_structured.call_args.kwargs
        assert "1200x628" in call_kwargs["user_prompt"]
        assert "1080x1080" in call_kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_default_platform(self):
        mock = _mock_claude()
        await generate_image_briefs(mock, _ctx())
        call_kwargs = mock.generate_structured.call_args.kwargs
        assert "LinkedIn Sponsored" in call_kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_invalid_platform_raises(self):
        mock = _mock_claude()
        with pytest.raises(ValueError, match="Unknown image platform"):
            await generate_image_briefs(mock, _ctx(), platforms=["snapchat"])


# ---------------------------------------------------------------------------
# Registration and attributes
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_registered_in_registry(self):
        from app.assets.prompts.base import GENERATOR_REGISTRY
        assert "image_brief" in GENERATOR_REGISTRY
        assert isinstance(GENERATOR_REGISTRY["image_brief"], ImageBriefGenerator)

    def test_generator_attributes(self):
        gen = ImageBriefGenerator()
        assert gen.asset_type == "image_brief"
        assert gen.model == "claude-sonnet-4-20250514"
        assert gen.output_schema is ImageBriefSetOutput
        assert gen.temperature == 0.6

    def test_does_not_need_social_proof(self):
        gen = ImageBriefGenerator()
        assert gen._needs_social_proof() is False
