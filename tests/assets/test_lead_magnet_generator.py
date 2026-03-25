"""Tests for BJC-169: Lead magnet PDF content generator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assets.context import AssetContext
from app.assets.generators.lead_magnet import (
    INDUSTRY_GUIDANCE,
    LEAD_MAGNET_FORMATS,
    LeadMagnetGenerator,
    generate_lead_magnet,
    map_output_to_pdf_input,
    select_lead_magnet_format,
)
from app.assets.models import LeadMagnetPDFInput, PDFSection
from app.assets.prompts.schemas import LeadMagnetOutput, LeadMagnetSectionOutput


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


def _sample_output(num_sections: int = 3) -> LeadMagnetOutput:
    sections = [
        LeadMagnetSectionOutput(
            heading=f"Section {i + 1}",
            body=f"Body for section {i + 1}.",
            bullets=[f"Item {j}" for j in range(3)],
            callout_box=f"Tip {i + 1}" if i == 0 else None,
        )
        for i in range(num_sections)
    ]
    return LeadMagnetOutput(
        title="Test Lead Magnet",
        subtitle="A subtitle for testing",
        sections=sections,
    )


def _mock_claude(return_value: LeadMagnetOutput | None = None) -> MagicMock:
    mock = MagicMock()
    mock.generate_structured = AsyncMock(return_value=return_value or _sample_output())
    return mock


# ---------------------------------------------------------------------------
# Format-specific prompt tests
# ---------------------------------------------------------------------------


class TestFormatPrompts:
    """Each of the 5 formats produces correct prompt instructions."""

    def _get_instructions(self, fmt: str, **ctx_kw: Any) -> str:
        gen = LeadMagnetGenerator()
        ctx = _ctx(**ctx_kw)
        return gen.build_asset_specific_instructions(ctx, format=fmt)

    def test_checklist_instructions(self):
        text = self._get_instructions("checklist")
        assert "CHECKLIST" in text
        assert "4–6 category sections" in text or "4-6 category sections" in text
        assert "15–25" in text or "15-25" in text
        assert "imperative action verb" in text
        assert "2,000" in text

    def test_ultimate_guide_instructions(self):
        text = self._get_instructions("ultimate_guide")
        assert "ULTIMATE GUIDE" in text
        assert "5 chapters" in text
        assert "800" in text and "1,800" in text or "800–1,800" in text
        assert "key takeaways" in text.lower()
        assert "5,500" in text

    def test_benchmark_report_instructions(self):
        text = self._get_instructions("benchmark_report")
        assert "BENCHMARK REPORT" in text
        assert "Executive summary" in text or "executive summary" in text
        assert "metric" in text.lower()
        assert "4,000" in text

    def test_template_toolkit_instructions(self):
        text = self._get_instructions("template_toolkit")
        assert "TEMPLATE" in text
        assert "step-by-step" in text.lower()
        assert "placeholder" in text.lower()
        assert "3,000" in text

    def test_state_of_industry_instructions(self):
        text = self._get_instructions("state_of_industry")
        assert "STATE OF THE INDUSTRY" in text
        assert "finding" in text.lower()
        assert "implication" in text.lower()
        assert "6,000" in text

    def test_unknown_format_raises(self):
        gen = LeadMagnetGenerator()
        ctx = _ctx()
        with pytest.raises(ValueError, match="Unknown lead magnet format"):
            gen.build_asset_specific_instructions(ctx, format="nonexistent")

    def test_default_format_is_checklist(self):
        gen = LeadMagnetGenerator()
        ctx = _ctx()
        text = gen.build_asset_specific_instructions(ctx)
        assert "CHECKLIST" in text


# ---------------------------------------------------------------------------
# Format selection logic
# ---------------------------------------------------------------------------


class TestFormatSelection:
    def test_compliance_angle_selects_checklist(self):
        result = select_lead_magnet_format("compliance audit", "lead_gen", "SaaS")
        assert result == "checklist"

    def test_guide_keyword_selects_ultimate_guide(self):
        result = select_lead_magnet_format("comprehensive guide to ABM", "education", "SaaS")
        assert result == "ultimate_guide"

    def test_benchmark_keyword_selects_benchmark_report(self):
        result = select_lead_magnet_format("benchmark data analysis", "lead_gen", "")
        assert result == "benchmark_report"

    def test_template_keyword_selects_template_toolkit(self):
        result = select_lead_magnet_format("template framework", "lead_gen", "")
        assert result == "template_toolkit"

    def test_trends_keyword_selects_state_of_industry(self):
        result = select_lead_magnet_format("industry trends", "thought_leadership", "")
        assert result == "state_of_industry"

    def test_empty_inputs_returns_valid_format(self):
        result = select_lead_magnet_format("", "", "")
        assert result in LEAD_MAGNET_FORMATS

    def test_none_inputs_returns_valid_format(self):
        result = select_lead_magnet_format(None, None, None)
        assert result in LEAD_MAGNET_FORMATS


# ---------------------------------------------------------------------------
# Output → rendering mapping
# ---------------------------------------------------------------------------


class TestOutputMapping:
    def test_maps_title_and_subtitle(self):
        output = _sample_output()
        ctx = _ctx()
        pdf_input = map_output_to_pdf_input(output, ctx)

        assert isinstance(pdf_input, LeadMagnetPDFInput)
        assert pdf_input.title == "Test Lead Magnet"
        assert pdf_input.subtitle == "A subtitle for testing"

    def test_maps_sections(self):
        output = _sample_output(num_sections=4)
        ctx = _ctx()
        pdf_input = map_output_to_pdf_input(output, ctx)

        assert len(pdf_input.sections) == 4
        for section in pdf_input.sections:
            assert isinstance(section, PDFSection)

    def test_maps_section_fields(self):
        output = _sample_output()
        ctx = _ctx()
        pdf_input = map_output_to_pdf_input(output, ctx)

        first = pdf_input.sections[0]
        assert first.heading == "Section 1"
        assert first.body == "Body for section 1."
        assert first.bullets == ["Item 0", "Item 1", "Item 2"]
        assert first.callout_box == "Tip 1"

    def test_null_callout_box(self):
        output = _sample_output()
        ctx = _ctx()
        pdf_input = map_output_to_pdf_input(output, ctx)

        # Second section has no callout_box
        assert pdf_input.sections[1].callout_box is None

    def test_empty_bullets_mapped_to_none(self):
        section = LeadMagnetSectionOutput(
            heading="Empty", body="No bullets here.", bullets=[], callout_box=None
        )
        output = LeadMagnetOutput(
            title="T", subtitle="S", sections=[section]
        )
        ctx = _ctx()
        pdf_input = map_output_to_pdf_input(output, ctx)
        assert pdf_input.sections[0].bullets is None

    def test_branding_uses_company_name(self):
        output = _sample_output()
        ctx = _ctx(company_name="AcmeCorp")
        pdf_input = map_output_to_pdf_input(output, ctx)

        assert pdf_input.branding.company_name == "AcmeCorp"

    def test_branding_defaults_when_no_company(self):
        output = _sample_output()
        ctx = _ctx(company_name="")
        pdf_input = map_output_to_pdf_input(output, ctx)

        assert pdf_input.branding.company_name == ""


# ---------------------------------------------------------------------------
# Two-pass generation for long formats
# ---------------------------------------------------------------------------


class TestTwoPassGeneration:
    @pytest.mark.asyncio
    async def test_ultimate_guide_uses_two_pass(self):
        """Two-pass generation calls Claude twice for ultimate_guide."""
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        ctx = _ctx()

        await gen.generate(mock, ctx, format="ultimate_guide")
        assert mock.generate_structured.call_count == 2

    @pytest.mark.asyncio
    async def test_state_of_industry_uses_two_pass(self):
        """Two-pass generation calls Claude twice for state_of_industry."""
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        ctx = _ctx()

        await gen.generate(mock, ctx, format="state_of_industry")
        assert mock.generate_structured.call_count == 2

    @pytest.mark.asyncio
    async def test_checklist_uses_single_pass(self):
        """Single-pass formats call Claude once."""
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        ctx = _ctx()

        await gen.generate(mock, ctx, format="checklist")
        assert mock.generate_structured.call_count == 1

    @pytest.mark.asyncio
    async def test_benchmark_report_uses_single_pass(self):
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        ctx = _ctx()

        await gen.generate(mock, ctx, format="benchmark_report")
        assert mock.generate_structured.call_count == 1

    @pytest.mark.asyncio
    async def test_template_toolkit_uses_single_pass(self):
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        ctx = _ctx()

        await gen.generate(mock, ctx, format="template_toolkit")
        assert mock.generate_structured.call_count == 1

    @pytest.mark.asyncio
    async def test_two_pass_outline_prompt_contains_outline_instructions(self):
        """First pass prompt asks for an outline."""
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        ctx = _ctx()

        await gen.generate(mock, ctx, format="ultimate_guide")

        first_call = mock.generate_structured.call_args_list[0]
        first_user_prompt = first_call.kwargs["user_prompt"]
        assert "outline" in first_user_prompt.lower()

    @pytest.mark.asyncio
    async def test_two_pass_expand_prompt_contains_outline_context(self):
        """Second pass prompt references the outline."""
        outline = _sample_output()
        mock = _mock_claude()
        mock.generate_structured = AsyncMock(return_value=outline)
        gen = LeadMagnetGenerator()
        ctx = _ctx()

        await gen.generate(mock, ctx, format="ultimate_guide")

        second_call = mock.generate_structured.call_args_list[1]
        second_user_prompt = second_call.kwargs["user_prompt"]
        assert "OUTLINE" in second_user_prompt
        assert "Section 1" in second_user_prompt

    @pytest.mark.asyncio
    async def test_two_pass_uses_correct_temperatures(self):
        """Outline pass uses lower temperature than expansion pass."""
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        ctx = _ctx()

        await gen.generate(mock, ctx, format="ultimate_guide")

        first_temp = mock.generate_structured.call_args_list[0].kwargs["temperature"]
        second_temp = mock.generate_structured.call_args_list[1].kwargs["temperature"]

        # Outline: format temp (0.7) - 0.1 = 0.6; Expand: format temp (0.7)
        assert first_temp < second_temp

    @pytest.mark.asyncio
    async def test_temperature_restored_after_generate(self):
        """Generator temperature is restored even after two-pass."""
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        ctx = _ctx()

        original = gen.temperature
        await gen.generate(mock, ctx, format="ultimate_guide")
        assert gen.temperature == original

    @pytest.mark.asyncio
    async def test_unknown_format_in_generate_raises(self):
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        ctx = _ctx()

        with pytest.raises(ValueError, match="Unknown lead magnet format"):
            await gen.generate(mock, ctx, format="nonexistent")


# ---------------------------------------------------------------------------
# Industry vertical prompt variations
# ---------------------------------------------------------------------------


class TestIndustryVerticals:
    def test_saas_industry_injects_guidance(self):
        gen = LeadMagnetGenerator()
        ctx = _ctx(industry="SaaS")
        text = gen.build_asset_specific_instructions(ctx, format="checklist")
        assert "Tech/SaaS" in text
        assert "MRR" in text or "churn" in text

    def test_healthcare_industry_injects_guidance(self):
        gen = LeadMagnetGenerator()
        ctx = _ctx(industry="Healthcare")
        text = gen.build_asset_specific_instructions(ctx, format="checklist")
        assert "Healthcare" in text
        assert "HIPAA" in text

    def test_financial_services_industry_injects_guidance(self):
        gen = LeadMagnetGenerator()
        ctx = _ctx(industry="Financial Services")
        text = gen.build_asset_specific_instructions(ctx, format="benchmark_report")
        assert "Financial Services" in text
        assert "FinCEN" in text or "SEC" in text

    def test_manufacturing_industry_injects_guidance(self):
        gen = LeadMagnetGenerator()
        ctx = _ctx(industry="Manufacturing")
        text = gen.build_asset_specific_instructions(ctx, format="template_toolkit")
        assert "Manufacturing" in text
        assert "ROI" in text or "process" in text.lower()

    def test_unknown_industry_includes_context(self):
        gen = LeadMagnetGenerator()
        ctx = _ctx(industry="Retail")
        text = gen.build_asset_specific_instructions(ctx, format="checklist")
        assert "Retail" in text
        assert "INDUSTRY CONTEXT" in text

    def test_no_industry_no_guidance(self):
        gen = LeadMagnetGenerator()
        ctx = _ctx(industry=None)
        text = gen.build_asset_specific_instructions(ctx, format="checklist")
        assert "INDUSTRY GUIDANCE" not in text
        assert "INDUSTRY CONTEXT" not in text

    def test_industry_guidance_varies_by_format(self):
        """Industry guidance is included regardless of format."""
        gen = LeadMagnetGenerator()
        for fmt in LEAD_MAGNET_FORMATS:
            ctx = _ctx(industry="Healthcare")
            text = gen.build_asset_specific_instructions(ctx, format=fmt)
            assert "Healthcare" in text


# ---------------------------------------------------------------------------
# Temperature per format
# ---------------------------------------------------------------------------


class TestTemperatureOverride:
    @pytest.mark.asyncio
    async def test_checklist_temperature(self):
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        await gen.generate(mock, _ctx(), format="checklist")
        temp = mock.generate_structured.call_args.kwargs["temperature"]
        assert temp == 0.3

    @pytest.mark.asyncio
    async def test_ultimate_guide_temperature(self):
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        await gen.generate(mock, _ctx(), format="ultimate_guide")
        # Second call (expand) uses format temperature
        temp = mock.generate_structured.call_args_list[1].kwargs["temperature"]
        assert temp == 0.7

    @pytest.mark.asyncio
    async def test_benchmark_report_temperature(self):
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        await gen.generate(mock, _ctx(), format="benchmark_report")
        temp = mock.generate_structured.call_args.kwargs["temperature"]
        assert temp == 0.5

    @pytest.mark.asyncio
    async def test_template_toolkit_temperature(self):
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        await gen.generate(mock, _ctx(), format="template_toolkit")
        temp = mock.generate_structured.call_args.kwargs["temperature"]
        assert temp == 0.4

    @pytest.mark.asyncio
    async def test_state_of_industry_temperature(self):
        mock = _mock_claude()
        gen = LeadMagnetGenerator()
        await gen.generate(mock, _ctx(), format="state_of_industry")
        temp = mock.generate_structured.call_args_list[1].kwargs["temperature"]
        assert temp == 0.6


# ---------------------------------------------------------------------------
# End-to-end convenience function
# ---------------------------------------------------------------------------


class TestGenerateLeadMagnet:
    @pytest.mark.asyncio
    async def test_returns_pdf_input(self):
        mock = _mock_claude()
        ctx = _ctx()
        result = await generate_lead_magnet(mock, ctx, format="checklist")
        assert isinstance(result, LeadMagnetPDFInput)
        assert result.title == "Test Lead Magnet"
        assert len(result.sections) == 3


# ---------------------------------------------------------------------------
# Generator registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_registered_in_registry(self):
        from app.assets.prompts.base import GENERATOR_REGISTRY

        assert "lead_magnet" in GENERATOR_REGISTRY
        assert isinstance(GENERATOR_REGISTRY["lead_magnet"], LeadMagnetGenerator)

    def test_generator_class_attributes(self):
        gen = LeadMagnetGenerator()
        assert gen.asset_type == "lead_magnet"
        assert gen.output_schema is LeadMagnetOutput
        assert gen.temperature == 0.5
