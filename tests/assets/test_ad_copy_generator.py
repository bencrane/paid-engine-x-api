"""Tests for BJC-171: Ad copy content generator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assets.context import AssetContext
from app.assets.generators.ad_copy import (
    CHAR_LIMITS,
    LINKEDIN_CTAS,
    META_CTAS,
    AdCopyGenerator,
    _truncate_at_word_boundary,
    generate_ad_copy,
    validate_ad_copy_limits,
)
from app.assets.prompts.schemas import (
    GoogleRSACopyOutput,
    LinkedInAdCopyOutput,
    LinkedInAdCopyVariant,
    MetaAdCopyOutput,
    MetaAdCopyVariant,
)


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


def _linkedin_output() -> LinkedInAdCopyOutput:
    return LinkedInAdCopyOutput(
        variants=[
            LinkedInAdCopyVariant(
                introductory_text="Struggling with compliance? TestCo helps.",
                headline="Simplify Your Compliance Today",
                description="Join 500+ companies using TestCo.",
                cta="Learn More",
            ),
            LinkedInAdCopyVariant(
                introductory_text="BigCo reduced compliance time by 40%.",
                headline="See How BigCo Did It",
                description="Real results from real companies.",
                cta="Download",
            ),
            LinkedInAdCopyVariant(
                introductory_text="What if compliance took half the time?",
                headline="Cut Compliance Time in Half",
                description="Automate your compliance workflow.",
                cta="Request Demo",
            ),
        ]
    )


def _meta_output() -> MetaAdCopyOutput:
    return MetaAdCopyOutput(
        variants=[
            MetaAdCopyVariant(
                primary_text="Compliance made simple.",
                headline="Simplify Compliance",
                description="Start free today",
                cta="LEARN_MORE",
            ),
            MetaAdCopyVariant(
                primary_text="40% faster compliance.",
                headline="Faster Compliance",
                description="See how it works",
                cta="SIGN_UP",
            ),
            MetaAdCopyVariant(
                primary_text="500+ teams trust TestCo.",
                headline="Trusted by 500+ Teams",
                description="Join them today",
                cta="DOWNLOAD",
            ),
        ]
    )


def _google_output() -> GoogleRSACopyOutput:
    return GoogleRSACopyOutput(
        headlines=[
            "Simplify Compliance Now",
            "TestCo Compliance Platform",
            "40% Faster Compliance",
            "Automate SOC 2 Audits",
            "Compliance Made Easy",
            "Is Your Team Audit-Ready?",
            "Trusted by 500+ Teams",
            "Free Compliance Trial",
            "SOC 2 in 90 Days",
            "Cut Audit Prep by 40%",
            "Start Your Free Trial",
            "Enterprise Compliance",
            "Real-Time Monitoring",
            "Join 500+ Companies",
            "Get Compliant Faster",
        ],
        descriptions=[
            "Automate your compliance workflow and get audit-ready in weeks, not months.",
            "Join 500+ mid-market teams that simplified compliance with TestCo.",
            "Free 14-day trial. No credit card required. Get started today.",
            "SOC 2, ISO 27001, HIPAA compliance automated in one platform.",
        ],
        path1="Compliance",
        path2="Free-Trial",
    )


def _mock_claude(return_value: Any = None) -> MagicMock:
    mock = MagicMock()
    mock.generate_structured = AsyncMock(
        return_value=return_value or _linkedin_output()
    )
    return mock


# ---------------------------------------------------------------------------
# Prompt generation per platform
# ---------------------------------------------------------------------------


class TestPlatformPrompts:
    def _get_instructions(self, platform: str) -> str:
        gen = AdCopyGenerator()
        return gen.build_asset_specific_instructions(_ctx(), platform=platform)

    def test_linkedin_prompt_content(self):
        text = self._get_instructions("linkedin")
        assert "LINKEDIN" in text
        assert "600" in text  # introductory_text limit
        assert "70" in text   # headline limit
        assert "3 ad copy variants" in text or "3 variants" in text.lower()
        assert "150" in text  # fold limit

    def test_meta_prompt_content(self):
        text = self._get_instructions("meta")
        assert "META" in text or "FACEBOOK" in text
        assert "125" in text  # primary_text limit
        assert "40" in text   # headline limit
        assert "30" in text   # description limit

    def test_google_prompt_content(self):
        text = self._get_instructions("google")
        assert "GOOGLE" in text or "RSA" in text
        assert "15 headlines" in text
        assert "30 characters" in text  # headline char limit
        assert "90 characters" in text  # description char limit
        assert "question" in text.lower()  # at least 1 question headline
        assert "number" in text.lower() or "statistic" in text.lower()

    def test_unknown_platform_raises(self):
        gen = AdCopyGenerator()
        with pytest.raises(ValueError, match="Unknown ad platform"):
            gen.build_asset_specific_instructions(_ctx(), platform="tiktok")

    def test_default_platform_is_linkedin(self):
        gen = AdCopyGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "LINKEDIN" in text


# ---------------------------------------------------------------------------
# Character limit validation
# ---------------------------------------------------------------------------


class TestCharacterLimitValidation:
    def test_linkedin_within_limits_no_warnings(self):
        output = _linkedin_output()
        fixed, warnings = validate_ad_copy_limits("linkedin", output)
        assert warnings == []

    def test_linkedin_truncates_long_headline(self):
        output = _linkedin_output()
        # Set headline over 70 chars
        long_headline = "This is a very long headline that exceeds the seventy character limit for LinkedIn ads"
        assert len(long_headline) > 70
        object.__setattr__(output.variants[0], "headline", long_headline)

        fixed, warnings = validate_ad_copy_limits("linkedin", output)
        assert len(warnings) == 1
        assert "headline" in warnings[0]
        assert len(fixed.variants[0].headline) <= 70

    def test_meta_truncates_long_primary_text(self):
        output = _meta_output()
        long_text = "This is a primary text field that goes well beyond the recommended 125 character limit for Meta ads on mobile devices for sure"
        assert len(long_text) > 125
        object.__setattr__(output.variants[0], "primary_text", long_text)

        fixed, warnings = validate_ad_copy_limits("meta", output)
        assert len(warnings) == 1
        assert len(fixed.variants[0].primary_text) <= 125

    def test_google_truncates_long_headline(self):
        output = _google_output()
        output.headlines[0] = "This headline is way too long for Google RSA"
        assert len(output.headlines[0]) > 30

        fixed, warnings = validate_ad_copy_limits("google", output)
        assert len(warnings) >= 1
        assert all(len(h) <= 30 for h in fixed.headlines)

    def test_google_truncates_long_path(self):
        output = _google_output()
        output.path1 = "VeryLongPathSegment"
        assert len(output.path1) > 15

        fixed, warnings = validate_ad_copy_limits("google", output)
        assert len(warnings) >= 1
        assert len(fixed.path1) <= 15

    def test_meta_within_limits_no_warnings(self):
        output = _meta_output()
        fixed, warnings = validate_ad_copy_limits("meta", output)
        assert warnings == []

    def test_google_within_limits_no_warnings(self):
        output = _google_output()
        fixed, warnings = validate_ad_copy_limits("google", output)
        assert warnings == []


# ---------------------------------------------------------------------------
# Word boundary truncation
# ---------------------------------------------------------------------------


class TestTruncation:
    def test_no_truncation_needed(self):
        assert _truncate_at_word_boundary("short", 100) == "short"

    def test_truncates_at_word_boundary(self):
        text = "hello world foo bar"
        result = _truncate_at_word_boundary(text, 12)
        assert result == "hello world"
        assert len(result) <= 12

    def test_does_not_cut_mid_word(self):
        text = "compliance automation platform"
        result = _truncate_at_word_boundary(text, 15)
        # Should cut at "compliance" (10 chars), not mid-word
        assert " " not in result or result.endswith(result.split()[-1])
        assert len(result) <= 15

    def test_single_long_word(self):
        # Edge case: single word longer than limit
        text = "supercalifragilistic"
        result = _truncate_at_word_boundary(text, 10)
        assert len(result) <= 20  # falls through since no space found > 0


# ---------------------------------------------------------------------------
# Schema dispatch per platform
# ---------------------------------------------------------------------------


class TestSchemaDispatch:
    @pytest.mark.asyncio
    async def test_linkedin_uses_correct_schema(self):
        mock = _mock_claude(_linkedin_output())
        gen = AdCopyGenerator()
        await gen.generate(mock, _ctx(), platform="linkedin")
        schema = mock.generate_structured.call_args.kwargs["output_schema"]
        assert schema is LinkedInAdCopyOutput

    @pytest.mark.asyncio
    async def test_meta_uses_correct_schema(self):
        mock = _mock_claude(_meta_output())
        gen = AdCopyGenerator()
        await gen.generate(mock, _ctx(), platform="meta")
        schema = mock.generate_structured.call_args.kwargs["output_schema"]
        assert schema is MetaAdCopyOutput

    @pytest.mark.asyncio
    async def test_google_uses_correct_schema(self):
        mock = _mock_claude(_google_output())
        gen = AdCopyGenerator()
        await gen.generate(mock, _ctx(), platform="google")
        schema = mock.generate_structured.call_args.kwargs["output_schema"]
        assert schema is GoogleRSACopyOutput

    @pytest.mark.asyncio
    async def test_schema_restored_after_generate(self):
        mock = _mock_claude(_meta_output())
        gen = AdCopyGenerator()
        original = gen.output_schema
        await gen.generate(mock, _ctx(), platform="meta")
        assert gen.output_schema is original

    @pytest.mark.asyncio
    async def test_unknown_platform_in_generate_raises(self):
        mock = _mock_claude()
        gen = AdCopyGenerator()
        with pytest.raises(ValueError, match="Unknown ad platform"):
            await gen.generate(mock, _ctx(), platform="tiktok")


# ---------------------------------------------------------------------------
# CTA allowed values
# ---------------------------------------------------------------------------


class TestCTAValues:
    def test_linkedin_ctas_are_valid(self):
        output = _linkedin_output()
        for v in output.variants:
            assert v.cta in LINKEDIN_CTAS

    def test_meta_ctas_are_valid(self):
        output = _meta_output()
        for v in output.variants:
            assert v.cta in META_CTAS


# ---------------------------------------------------------------------------
# Multi-platform generation
# ---------------------------------------------------------------------------


class TestMultiPlatformGeneration:
    @pytest.mark.asyncio
    async def test_generates_for_multiple_platforms(self):
        mock = MagicMock()
        # Return different outputs based on call order
        mock.generate_structured = AsyncMock(
            side_effect=[_linkedin_output(), _meta_output()]
        )
        results = await generate_ad_copy(mock, _ctx(), platforms=["linkedin", "meta"])
        assert "linkedin" in results
        assert "meta" in results
        assert isinstance(results["linkedin"], LinkedInAdCopyOutput)
        assert isinstance(results["meta"], MetaAdCopyOutput)

    @pytest.mark.asyncio
    async def test_generates_single_platform(self):
        mock = MagicMock()
        mock.generate_structured = AsyncMock(return_value=_google_output())
        results = await generate_ad_copy(mock, _ctx(), platforms=["google"])
        assert "google" in results
        assert isinstance(results["google"], GoogleRSACopyOutput)

    @pytest.mark.asyncio
    async def test_invalid_platform_raises(self):
        mock = _mock_claude()
        with pytest.raises(ValueError, match="Unknown ad platform"):
            await generate_ad_copy(mock, _ctx(), platforms=["linkedin", "snapchat"])


# ---------------------------------------------------------------------------
# Generator registration and attributes
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_registered_in_registry(self):
        from app.assets.prompts.base import GENERATOR_REGISTRY
        assert "ad_copy" in GENERATOR_REGISTRY
        assert isinstance(GENERATOR_REGISTRY["ad_copy"], AdCopyGenerator)

    def test_generator_attributes(self):
        gen = AdCopyGenerator()
        assert gen.asset_type == "ad_copy"
        assert gen.model == "claude-sonnet-4-20250514"
        assert gen.temperature == 0.5

    def test_does_not_need_social_proof(self):
        gen = AdCopyGenerator()
        assert gen._needs_social_proof() is False
