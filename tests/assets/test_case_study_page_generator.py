"""Tests for BJC-176: Case study page content generator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assets.context import AssetContext
from app.assets.generators.case_study_page import (
    CaseStudyPageGenerator,
    generate_case_study_page,
    map_output_to_case_study_page_input,
)
from app.assets.models import CaseStudyPageInput, MetricCallout, Section
from app.assets.prompts.schemas import (
    CaseStudyContentOutput,
    CaseStudyMetricOutput,
    CaseStudyNarrativeSection,
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
        case_studies=[
            {
                "customer_name": "BigCo",
                "customer_industry": "Financial Services",
                "problem": "Manual audit processes took 6 weeks per quarter",
                "solution": "Automated compliance monitoring with TestCo",
                "results": {"roi": "3x", "time_saved": "40%", "pipeline": "$2.1M"},
                "quote": {
                    "text": "TestCo transformed our compliance workflow.",
                    "author": "Jane Smith",
                    "title": "VP Compliance",
                },
            }
        ],
        testimonials=[{"quote": "Great", "author": "J", "title": "CTO", "company": "X"}],
    )
    defaults.update(overrides)
    return AssetContext(**defaults)


def _case_study_output(
    with_quote: bool = True,
) -> CaseStudyContentOutput:
    sections = [
        CaseStudyNarrativeSection(
            heading="The Situation",
            body="BigCo is a financial services company with 500 employees...",
            bullets=["500+ employees", "Regulated industry"],
        ),
        CaseStudyNarrativeSection(
            heading="The Challenge",
            body="Manual audit processes consumed 6 weeks per quarter...",
            bullets=["6-week audit cycles", "3 FTEs dedicated to compliance"],
        ),
        CaseStudyNarrativeSection(
            heading="The Solution",
            body="BigCo deployed TestCo's automated compliance platform...",
        ),
        CaseStudyNarrativeSection(
            heading="The Results",
            body="Within 90 days, BigCo saw dramatic improvements...",
            bullets=["3x ROI", "40% time saved", "$2.1M pipeline"],
        ),
    ]
    metrics = [
        CaseStudyMetricOutput(value="3x", label="ROI"),
        CaseStudyMetricOutput(value="40%", label="Time saved"),
        CaseStudyMetricOutput(value="$2.1M", label="Pipeline generated"),
    ]
    return CaseStudyContentOutput(
        headline="How BigCo Cut Audit Prep by 40%",
        sections=sections,
        metrics=metrics,
        quote_text="TestCo transformed our compliance workflow." if with_quote else None,
        quote_author="Jane Smith" if with_quote else None,
        quote_title="VP Compliance" if with_quote else None,
        cta_text="Get Similar Results",
    )


def _mock_claude(return_value: Any = None) -> MagicMock:
    mock = MagicMock()
    mock.generate_structured = AsyncMock(
        return_value=return_value or _case_study_output()
    )
    return mock


# ---------------------------------------------------------------------------
# Prompt case study data injection
# ---------------------------------------------------------------------------


class TestCaseStudyDataInjection:
    def test_case_study_data_in_prompt(self):
        gen = CaseStudyPageGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), case_study_index=0)
        assert "BigCo" in text
        assert "Financial Services" in text
        assert "3x" in text or "roi" in text.lower()

    def test_case_study_problem_in_prompt(self):
        gen = CaseStudyPageGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), case_study_index=0)
        assert "audit" in text.lower() or "Manual" in text

    def test_case_study_quote_in_prompt(self):
        gen = CaseStudyPageGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), case_study_index=0)
        assert "transformed" in text.lower() or "Jane Smith" in text

    def test_missing_case_study_handled(self):
        ctx = _ctx(case_studies=[])
        gen = CaseStudyPageGenerator()
        text = gen.build_asset_specific_instructions(ctx, case_study_index=0)
        assert "No case study data" in text or "placeholder" in text.lower()

    def test_out_of_range_index_handled(self):
        gen = CaseStudyPageGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), case_study_index=99)
        assert "No case study data" in text or "placeholder" in text.lower()


# ---------------------------------------------------------------------------
# Narrative structure tests
# ---------------------------------------------------------------------------


class TestNarrativeStructure:
    def test_four_sections_in_prompt(self):
        gen = CaseStudyPageGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        for section in ("SITUATION", "CHALLENGE", "SOLUTION", "RESULTS"):
            assert section in text.upper()

    def test_word_count_guidance(self):
        gen = CaseStudyPageGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "200" in text and "400" in text

    def test_headline_format_guidance(self):
        gen = CaseStudyPageGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "How" in text
        assert "achieved" in text.lower() or "Key Result" in text

    def test_metrics_guidance(self):
        gen = CaseStudyPageGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "2-4" in text or ("2" in text and "4" in text and "metric" in text.lower())


# ---------------------------------------------------------------------------
# Output mapping tests
# ---------------------------------------------------------------------------


class TestOutputMapping:
    def test_maps_to_case_study_page_input(self):
        output = _case_study_output()
        result = map_output_to_case_study_page_input(output, _ctx())
        assert isinstance(result, CaseStudyPageInput)

    def test_sections_mapped(self):
        output = _case_study_output()
        result = map_output_to_case_study_page_input(output, _ctx())
        assert len(result.sections) == 4
        assert result.sections[0].heading == "The Situation"
        assert isinstance(result.sections[0], Section)

    def test_metrics_mapped(self):
        output = _case_study_output()
        result = map_output_to_case_study_page_input(output, _ctx())
        assert len(result.metrics) == 3
        assert result.metrics[0].value == "3x"
        assert result.metrics[0].label == "ROI"
        assert isinstance(result.metrics[0], MetricCallout)

    def test_quote_mapped(self):
        output = _case_study_output(with_quote=True)
        result = map_output_to_case_study_page_input(output, _ctx())
        assert result.quote_text == "TestCo transformed our compliance workflow."
        assert result.quote_author == "Jane Smith"
        assert result.quote_title == "VP Compliance"

    def test_missing_quote_mapped_as_none(self):
        output = _case_study_output(with_quote=False)
        result = map_output_to_case_study_page_input(output, _ctx())
        assert result.quote_text is None
        assert result.quote_author is None
        assert result.quote_title is None

    def test_customer_name_from_case_study(self):
        output = _case_study_output()
        result = map_output_to_case_study_page_input(output, _ctx(), case_study_index=0)
        assert result.customer_name == "BigCo"

    def test_branding_included(self):
        output = _case_study_output()
        result = map_output_to_case_study_page_input(output, _ctx())
        assert result.branding.company_name == "TestCo"

    def test_cta_text_mapped(self):
        output = _case_study_output()
        result = map_output_to_case_study_page_input(output, _ctx())
        assert result.cta_text == "Get Similar Results"


# ---------------------------------------------------------------------------
# Convenience function tests
# ---------------------------------------------------------------------------


class TestGenerateCaseStudyPage:
    @pytest.mark.asyncio
    async def test_returns_case_study_page_input(self):
        mock = _mock_claude()
        result = await generate_case_study_page(mock, _ctx())
        assert isinstance(result, CaseStudyPageInput)

    @pytest.mark.asyncio
    async def test_passes_case_study_index(self):
        mock = _mock_claude()
        await generate_case_study_page(mock, _ctx(), case_study_index=0)
        call_kwargs = mock.generate_structured.call_args.kwargs
        assert "BigCo" in call_kwargs["user_prompt"]


# ---------------------------------------------------------------------------
# Registration and attributes
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_registered_in_registry(self):
        from app.assets.prompts.base import GENERATOR_REGISTRY
        assert "case_study_page" in GENERATOR_REGISTRY
        assert isinstance(GENERATOR_REGISTRY["case_study_page"], CaseStudyPageGenerator)

    def test_generator_attributes(self):
        gen = CaseStudyPageGenerator()
        assert gen.asset_type == "case_study_page"
        assert gen.model == "claude-opus-4-20250514"
        assert gen.output_schema is CaseStudyContentOutput
        assert gen.temperature == 0.6

    def test_needs_social_proof(self):
        gen = CaseStudyPageGenerator()
        assert gen._needs_social_proof() is True
