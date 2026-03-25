"""Tests for BJC-174: LinkedIn Document Ad (Carousel) content generator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assets.context import AssetContext
from app.assets.generators.document_ad import (
    VALID_PATTERNS,
    DocumentAdGenerator,
    generate_document_ad,
    map_output_to_document_ad_input,
)
from app.assets.models import DocumentAdInput, Slide
from app.assets.prompts.schemas import DocumentAdOutput, SlideOutput


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


def _slide_output(
    headline: str = "Slide headline",
    body: str | None = "Slide body text",
    stat_callout: str | None = None,
    stat_label: str | None = None,
    is_cta: bool = False,
    cta_text: str | None = None,
) -> SlideOutput:
    return SlideOutput(
        headline=headline,
        body=body,
        stat_callout=stat_callout,
        stat_label=stat_label,
        is_cta_slide=is_cta,
        cta_text=cta_text,
    )


def _document_ad_output(num_slides: int = 6) -> DocumentAdOutput:
    slides = [_slide_output(headline=f"Slide {i+1}") for i in range(num_slides - 1)]
    slides.append(
        _slide_output(
            headline="Take Action Now",
            body="Get started today",
            is_cta=True,
            cta_text="Download the Guide",
        )
    )
    return DocumentAdOutput(slides=slides, aspect_ratio="1:1")


def _mock_claude(return_value: Any = None) -> MagicMock:
    mock = MagicMock()
    mock.generate_structured = AsyncMock(
        return_value=return_value or _document_ad_output()
    )
    return mock


# ---------------------------------------------------------------------------
# Narrative pattern tests
# ---------------------------------------------------------------------------


class TestNarrativePatterns:
    def _get_instructions(self, pattern: str) -> str:
        gen = DocumentAdGenerator()
        return gen.build_asset_specific_instructions(_ctx(), pattern=pattern)

    def test_problem_solution_pattern(self):
        text = self._get_instructions("problem_solution")
        assert "Problem" in text
        assert "Solution" in text
        assert "Proof" in text
        assert "Hook" in text

    def test_listicle_pattern(self):
        text = self._get_instructions("listicle")
        assert "Listicle" in text or "listicle" in text.lower()
        assert "sign" in text.lower() or "Sign" in text
        assert "Summary" in text or "so-what" in text

    def test_data_story_pattern(self):
        text = self._get_instructions("data_story")
        assert "Data Story" in text or "data" in text.lower()
        assert "stat" in text.lower()

    def test_different_patterns_produce_different_prompts(self):
        p1 = self._get_instructions("problem_solution")
        p2 = self._get_instructions("listicle")
        p3 = self._get_instructions("data_story")
        assert p1 != p2
        assert p2 != p3
        assert p1 != p3

    def test_unknown_pattern_raises(self):
        gen = DocumentAdGenerator()
        with pytest.raises(ValueError, match="Unknown carousel pattern"):
            gen.build_asset_specific_instructions(_ctx(), pattern="timeline")

    def test_default_pattern_is_problem_solution(self):
        gen = DocumentAdGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "Problem" in text and "Solution" in text and "Proof" in text


# ---------------------------------------------------------------------------
# Slide constraint tests
# ---------------------------------------------------------------------------


class TestSlideConstraints:
    def test_slide_count_in_prompt(self):
        gen = DocumentAdGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "5-8" in text or ("5" in text and "8" in text)

    def test_headline_char_limit_in_prompt(self):
        gen = DocumentAdGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "50 char" in text.lower() or "max 50" in text.lower()

    def test_body_char_limit_in_prompt(self):
        gen = DocumentAdGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "120 char" in text.lower() or "max 120" in text.lower()

    def test_cta_slide_required_in_prompt(self):
        gen = DocumentAdGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "is_cta_slide" in text
        assert "last slide" in text.lower() or "LAST slide" in text


# ---------------------------------------------------------------------------
# Aspect ratio tests
# ---------------------------------------------------------------------------


class TestAspectRatio:
    def test_aspect_ratio_guidance_in_prompt(self):
        gen = DocumentAdGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "1:1" in text
        assert "4:5" in text

    def test_output_mapping_preserves_aspect_ratio(self):
        output = DocumentAdOutput(
            slides=[_slide_output() for _ in range(4)]
            + [_slide_output(is_cta=True, cta_text="Go")],
            aspect_ratio="4:5",
        )
        result = map_output_to_document_ad_input(output, _ctx())
        assert result.aspect_ratio == "4:5"


# ---------------------------------------------------------------------------
# Output mapping tests
# ---------------------------------------------------------------------------


class TestOutputMapping:
    def test_maps_to_document_ad_input(self):
        output = _document_ad_output(6)
        result = map_output_to_document_ad_input(output, _ctx())
        assert isinstance(result, DocumentAdInput)
        assert len(result.slides) == 6

    def test_slides_mapped_correctly(self):
        output = _document_ad_output(6)
        result = map_output_to_document_ad_input(output, _ctx())
        # Last slide is CTA
        last = result.slides[-1]
        assert last.is_cta_slide is True
        assert last.cta_text == "Download the Guide"
        # Non-CTA slides
        for slide in result.slides[:-1]:
            assert slide.is_cta_slide is False

    def test_branding_included(self):
        result = map_output_to_document_ad_input(_document_ad_output(), _ctx())
        assert result.branding.company_name == "TestCo"

    def test_stat_callout_mapped(self):
        output = DocumentAdOutput(
            slides=[
                _slide_output(stat_callout="47%", stat_label="Time saved"),
                _slide_output(),
                _slide_output(),
                _slide_output(),
                _slide_output(is_cta=True, cta_text="Go"),
            ],
            aspect_ratio="1:1",
        )
        result = map_output_to_document_ad_input(output, _ctx())
        assert result.slides[0].stat_callout == "47%"
        assert result.slides[0].stat_label == "Time saved"


# ---------------------------------------------------------------------------
# Convenience function tests
# ---------------------------------------------------------------------------


class TestGenerateDocumentAd:
    @pytest.mark.asyncio
    async def test_returns_document_ad_input(self):
        mock = _mock_claude()
        result = await generate_document_ad(mock, _ctx())
        assert isinstance(result, DocumentAdInput)

    @pytest.mark.asyncio
    async def test_passes_pattern_to_generator(self):
        mock = _mock_claude()
        await generate_document_ad(mock, _ctx(), pattern="listicle")
        call_kwargs = mock.generate_structured.call_args.kwargs
        assert "Listicle" in call_kwargs["user_prompt"] or "listicle" in call_kwargs["user_prompt"].lower()

    @pytest.mark.asyncio
    async def test_invalid_pattern_raises(self):
        mock = _mock_claude()
        with pytest.raises(ValueError, match="Unknown carousel pattern"):
            await generate_document_ad(mock, _ctx(), pattern="timeline")


# ---------------------------------------------------------------------------
# Registration and attributes
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_registered_in_registry(self):
        from app.assets.prompts.base import GENERATOR_REGISTRY
        assert "document_ad" in GENERATOR_REGISTRY
        assert isinstance(GENERATOR_REGISTRY["document_ad"], DocumentAdGenerator)

    def test_generator_attributes(self):
        gen = DocumentAdGenerator()
        assert gen.asset_type == "document_ad"
        assert gen.model == "claude-opus-4-20250514"
        assert gen.output_schema is DocumentAdOutput
        assert gen.temperature == 0.5

    def test_needs_social_proof(self):
        gen = DocumentAdGenerator()
        assert gen._needs_social_proof() is True
