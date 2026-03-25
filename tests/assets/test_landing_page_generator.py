"""Tests for BJC-170: Landing page content generator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assets.context import AssetContext
from app.assets.generators.landing_page import (
    DEFAULT_FORM_FIELDS,
    LandingPageGenerator,
    _build_branding,
    _build_social_proof,
    generate_landing_page,
    map_case_study_page,
    map_demo_request_page,
    map_lead_magnet_page,
    map_webinar_page,
    select_landing_page_template,
)
from app.assets.models import (
    BrandingConfig,
    CaseStudyPageInput,
    DemoRequestPageInput,
    FormField,
    LeadMagnetPageInput,
    MetricCallout,
    Section,
    SocialProofConfig,
    WebinarPageInput,
)
from app.assets.prompts.schemas import (
    CaseStudyPageOutput,
    DemoRequestPageOutput,
    LandingPageSectionOutput,
    LeadMagnetPageOutput,
    WebinarPageOutput,
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
        case_studies=[{
            "customer_name": "BigCo",
            "problem": "Manual compliance tracking",
            "solution": "Automated platform",
            "results": {"roi": "3x", "time_saved": "40%"},
            "quote": {"text": "Transformed our workflow", "author": "Jane", "title": "CTO"},
        }],
        testimonials=[{"quote": "Great product", "author": "J", "title": "CTO", "company": "X"}],
        customer_logos=["logo1.png", "logo2.png"],
    )
    defaults.update(overrides)
    return AssetContext(**defaults)


def _lead_magnet_page_output() -> LeadMagnetPageOutput:
    return LeadMagnetPageOutput(
        headline="The Complete Security Compliance Checklist",
        subhead="Everything mid-market SaaS teams need to stay audit-ready.",
        value_props=[
            "23-point checklist covering all SOC 2 requirements",
            "Industry-specific guidance for SaaS companies",
            "Actionable steps you can implement today",
        ],
        cta_text="Get My Free Checklist",
    )


def _case_study_page_output() -> CaseStudyPageOutput:
    return CaseStudyPageOutput(
        customer_name="BigCo",
        headline="How BigCo Cut Compliance Time by 40%",
        sections=[
            LandingPageSectionOutput(
                heading="The Situation", body="BigCo is a mid-market SaaS company.",
                bullets=["100+ employees", "Series B funded"], callout=None,
            ),
            LandingPageSectionOutput(
                heading="The Challenge", body="Manual processes slowed them down.",
                bullets=None, callout="40 hours/month on compliance",
            ),
            LandingPageSectionOutput(
                heading="The Solution", body="They adopted TestCo's platform.",
                bullets=["Automated workflows", "Real-time dashboards"], callout=None,
            ),
            LandingPageSectionOutput(
                heading="The Results", body="Dramatic time and cost savings.",
                bullets=["40% time reduction", "3x ROI"], callout=None,
            ),
        ],
        metrics=[{"value": "3x", "label": "ROI"}, {"value": "40%", "label": "Time Saved"}],
        quote_text="Transformed our workflow",
        quote_author="Jane",
        quote_title="CTO",
        cta_text="Get Similar Results",
    )


def _webinar_page_output() -> WebinarPageOutput:
    return WebinarPageOutput(
        event_name="Mastering B2B Compliance",
        headline="Learn the 5 Strategies Top Teams Use to Stay Audit-Ready",
        agenda=[
            "Discover the top compliance pitfalls",
            "Learn automation best practices",
            "Master continuous monitoring",
            "Understand SOC 2 requirements",
            "Build a compliance culture",
        ],
        cta_text="Reserve My Spot",
    )


def _demo_request_page_output() -> DemoRequestPageOutput:
    return DemoRequestPageOutput(
        headline="Tired of Spending 40 Hours on Compliance?",
        subhead="Manual processes are costing you time and accuracy. See how automation helps.",
        benefits=[
            LandingPageSectionOutput(
                heading="Cut Compliance Time in Half", body="Automate repetitive tasks.",
                bullets=["Automated evidence collection", "Real-time alerts"],
                callout="Average 40% time reduction",
            ),
            LandingPageSectionOutput(
                heading="Stay Audit-Ready 24/7", body="Continuous monitoring.",
                bullets=None, callout=None,
            ),
            LandingPageSectionOutput(
                heading="Reduce Risk", body="Proactive compliance management.",
                bullets=["Risk scoring", "Gap analysis"], callout=None,
            ),
        ],
        cta_text="See It in Action",
    )


def _mock_claude(return_value: Any = None) -> MagicMock:
    mock = MagicMock()
    mock.generate_structured = AsyncMock(
        return_value=return_value or _lead_magnet_page_output()
    )
    return mock


# ---------------------------------------------------------------------------
# Prompt generation for each template type
# ---------------------------------------------------------------------------


class TestTemplatePrompts:
    """Each of the 4 template types produces correct prompt instructions."""

    def _get_instructions(self, template_type: str, **ctx_kw: Any) -> str:
        gen = LandingPageGenerator()
        ctx = _ctx(**ctx_kw)
        return gen.build_asset_specific_instructions(ctx, template_type=template_type)

    def test_lead_magnet_download_instructions(self):
        text = self._get_instructions("lead_magnet_download")
        assert "LEAD MAGNET DOWNLOAD" in text
        assert "headline" in text.lower()
        assert "value_props" in text or "value propositions" in text.lower()
        assert "curiosity" in text.lower()

    def test_case_study_instructions(self):
        text = self._get_instructions("case_study")
        assert "CASE STUDY" in text
        assert "narrative" in text.lower() or "story" in text.lower()
        assert "metrics" in text.lower()
        assert "BigCo" in text  # case study data injected

    def test_case_study_without_case_study_data(self):
        text = self._get_instructions("case_study", case_studies=[])
        assert "CASE STUDY" in text
        assert "CASE STUDY DATA" not in text

    def test_webinar_instructions(self):
        text = self._get_instructions("webinar")
        assert "WEBINAR" in text
        assert "agenda" in text.lower()
        assert "FOMO" in text or "urgency" in text.lower()

    def test_demo_request_instructions(self):
        text = self._get_instructions("demo_request")
        assert "DEMO REQUEST" in text
        assert "pain" in text.lower()
        assert "problem-agitation-solution" in text.lower() or "agitate" in text.lower()

    def test_unknown_template_raises(self):
        gen = LandingPageGenerator()
        ctx = _ctx()
        with pytest.raises(ValueError, match="Unknown landing page template"):
            gen.build_asset_specific_instructions(ctx, template_type="nonexistent")

    def test_default_template_is_lead_magnet_download(self):
        gen = LandingPageGenerator()
        ctx = _ctx()
        text = gen.build_asset_specific_instructions(ctx)
        assert "LEAD MAGNET DOWNLOAD" in text


# ---------------------------------------------------------------------------
# Template selection logic
# ---------------------------------------------------------------------------


class TestTemplateSelection:
    def test_webinar_objective_selects_webinar(self):
        ctx = _ctx(objective="webinar registration")
        assert select_landing_page_template(ctx) == "webinar"

    def test_event_angle_selects_webinar(self):
        ctx = _ctx(angle="event promotion")
        assert select_landing_page_template(ctx) == "webinar"

    def test_demo_objective_selects_demo_request(self):
        ctx = _ctx(objective="demo request")
        assert select_landing_page_template(ctx) == "demo_request"

    def test_consultation_objective_selects_demo_request(self):
        ctx = _ctx(objective="consultation booking")
        assert select_landing_page_template(ctx) == "demo_request"

    def test_case_study_angle_with_data_selects_case_study(self):
        ctx = _ctx(
            angle="case study showcase",
            case_studies=[{"customer_name": "BigCo", "results": {"roi": "3x"}}],
        )
        assert select_landing_page_template(ctx) == "case_study"

    def test_case_study_angle_without_data_selects_lead_magnet(self):
        ctx = _ctx(angle="case study showcase", case_studies=[])
        assert select_landing_page_template(ctx) == "lead_magnet_download"

    def test_default_selects_lead_magnet_download(self):
        ctx = _ctx(objective="lead_gen", angle="Security compliance")
        assert select_landing_page_template(ctx) == "lead_magnet_download"

    def test_empty_context_selects_lead_magnet_download(self):
        ctx = _ctx(objective=None, angle=None, case_studies=[])
        assert select_landing_page_template(ctx) == "lead_magnet_download"


# ---------------------------------------------------------------------------
# Output mapping: LeadMagnetPageOutput → LeadMagnetPageInput
# ---------------------------------------------------------------------------


class TestLeadMagnetPageMapping:
    def test_maps_headline_and_subhead(self):
        output = _lead_magnet_page_output()
        ctx = _ctx()
        result = map_lead_magnet_page(output, ctx)

        assert isinstance(result, LeadMagnetPageInput)
        assert result.headline == "The Complete Security Compliance Checklist"
        assert "audit-ready" in result.subhead

    def test_maps_value_props(self):
        output = _lead_magnet_page_output()
        result = map_lead_magnet_page(output, _ctx())
        assert len(result.value_props) == 3
        assert "SOC 2" in result.value_props[0]

    def test_maps_cta_text(self):
        output = _lead_magnet_page_output()
        result = map_lead_magnet_page(output, _ctx())
        assert result.cta_text == "Get My Free Checklist"

    def test_includes_default_form_fields(self):
        output = _lead_magnet_page_output()
        result = map_lead_magnet_page(output, _ctx())
        assert len(result.form_fields) == 4
        field_names = [f.name for f in result.form_fields]
        assert "email" in field_names
        assert "first_name" in field_names

    def test_social_proof_from_testimonial(self):
        output = _lead_magnet_page_output()
        ctx = _ctx()
        result = map_lead_magnet_page(output, ctx)
        assert result.social_proof is not None
        assert result.social_proof.type == "quote"
        assert result.social_proof.quote_text == "Great product"

    def test_social_proof_from_logos_when_no_testimonials(self):
        output = _lead_magnet_page_output()
        ctx = _ctx(testimonials=[], customer_logos=["a.png", "b.png"])
        result = map_lead_magnet_page(output, ctx)
        assert result.social_proof is not None
        assert result.social_proof.type == "logos"
        assert result.social_proof.logos == ["a.png", "b.png"]

    def test_no_social_proof_when_no_data(self):
        output = _lead_magnet_page_output()
        ctx = _ctx(testimonials=[], customer_logos=[])
        result = map_lead_magnet_page(output, ctx)
        assert result.social_proof is None


# ---------------------------------------------------------------------------
# Output mapping: CaseStudyPageOutput → CaseStudyPageInput
# ---------------------------------------------------------------------------


class TestCaseStudyPageMapping:
    def test_maps_customer_and_headline(self):
        output = _case_study_page_output()
        result = map_case_study_page(output, _ctx())
        assert isinstance(result, CaseStudyPageInput)
        assert result.customer_name == "BigCo"
        assert "BigCo" in result.headline

    def test_maps_sections(self):
        output = _case_study_page_output()
        result = map_case_study_page(output, _ctx())
        assert len(result.sections) == 4
        assert all(isinstance(s, Section) for s in result.sections)
        assert result.sections[0].heading == "The Situation"

    def test_maps_section_callout(self):
        output = _case_study_page_output()
        result = map_case_study_page(output, _ctx())
        assert result.sections[1].callout == "40 hours/month on compliance"

    def test_maps_metrics(self):
        output = _case_study_page_output()
        result = map_case_study_page(output, _ctx())
        assert len(result.metrics) == 2
        assert all(isinstance(m, MetricCallout) for m in result.metrics)
        assert result.metrics[0].value == "3x"
        assert result.metrics[0].label == "ROI"

    def test_maps_quote(self):
        output = _case_study_page_output()
        result = map_case_study_page(output, _ctx())
        assert result.quote_text == "Transformed our workflow"
        assert result.quote_author == "Jane"
        assert result.quote_title == "CTO"

    def test_no_case_study_form_fields_by_default(self):
        output = _case_study_page_output()
        result = map_case_study_page(output, _ctx())
        assert result.form_fields == []


# ---------------------------------------------------------------------------
# Output mapping: WebinarPageOutput → WebinarPageInput
# ---------------------------------------------------------------------------


class TestWebinarPageMapping:
    def test_maps_event_info(self):
        output = _webinar_page_output()
        result = map_webinar_page(output, _ctx(), event_date="2026-04-15")
        assert isinstance(result, WebinarPageInput)
        assert result.event_name == "Mastering B2B Compliance"
        assert result.event_date == "2026-04-15"

    def test_maps_agenda(self):
        output = _webinar_page_output()
        result = map_webinar_page(output, _ctx())
        assert len(result.agenda) == 5

    def test_maps_speakers(self):
        output = _webinar_page_output()
        speakers = [{"name": "John", "title": "CEO"}]
        result = map_webinar_page(output, _ctx(), speakers=speakers)
        assert result.speakers == [{"name": "John", "title": "CEO"}]

    def test_default_speakers_empty(self):
        output = _webinar_page_output()
        result = map_webinar_page(output, _ctx())
        assert result.speakers == []

    def test_default_event_date(self):
        output = _webinar_page_output()
        result = map_webinar_page(output, _ctx())
        assert result.event_date == "TBD"

    def test_includes_webinar_form_fields(self):
        output = _webinar_page_output()
        result = map_webinar_page(output, _ctx())
        assert len(result.form_fields) == 5
        field_names = [f.name for f in result.form_fields]
        assert "email" in field_names
        assert "last_name" in field_names


# ---------------------------------------------------------------------------
# Output mapping: DemoRequestPageOutput → DemoRequestPageInput
# ---------------------------------------------------------------------------


class TestDemoRequestPageMapping:
    def test_maps_headline_and_subhead(self):
        output = _demo_request_page_output()
        result = map_demo_request_page(output, _ctx())
        assert isinstance(result, DemoRequestPageInput)
        assert "40 Hours" in result.headline
        assert "automation" in result.subhead.lower()

    def test_maps_benefits(self):
        output = _demo_request_page_output()
        result = map_demo_request_page(output, _ctx())
        assert len(result.benefits) == 3
        assert all(isinstance(b, Section) for b in result.benefits)

    def test_maps_benefit_bullets(self):
        output = _demo_request_page_output()
        result = map_demo_request_page(output, _ctx())
        assert result.benefits[0].bullets == [
            "Automated evidence collection", "Real-time alerts"
        ]
        assert result.benefits[1].bullets is None

    def test_maps_benefit_callout(self):
        output = _demo_request_page_output()
        result = map_demo_request_page(output, _ctx())
        assert result.benefits[0].callout == "Average 40% time reduction"

    def test_trust_signals_from_testimonial(self):
        output = _demo_request_page_output()
        ctx = _ctx()
        result = map_demo_request_page(output, ctx)
        assert result.trust_signals is not None
        assert result.trust_signals.type == "quote"

    def test_includes_demo_form_fields(self):
        output = _demo_request_page_output()
        result = map_demo_request_page(output, _ctx())
        assert len(result.form_fields) == 6
        field_names = [f.name for f in result.form_fields]
        assert "phone" in field_names


# ---------------------------------------------------------------------------
# Default form fields
# ---------------------------------------------------------------------------


class TestDefaultFormFields:
    def test_lead_magnet_has_4_fields(self):
        fields = DEFAULT_FORM_FIELDS["lead_magnet_download"]
        assert len(fields) == 4
        assert all(isinstance(f, FormField) for f in fields)

    def test_lead_magnet_email_is_required(self):
        fields = DEFAULT_FORM_FIELDS["lead_magnet_download"]
        email_field = next(f for f in fields if f.name == "email")
        assert email_field.required is True
        assert email_field.type == "email"

    def test_case_study_has_no_fields(self):
        assert DEFAULT_FORM_FIELDS["case_study"] == []

    def test_webinar_has_5_fields(self):
        fields = DEFAULT_FORM_FIELDS["webinar"]
        assert len(fields) == 5

    def test_demo_request_phone_is_optional(self):
        fields = DEFAULT_FORM_FIELDS["demo_request"]
        phone_field = next(f for f in fields if f.name == "phone")
        assert phone_field.required is False
        assert phone_field.type == "tel"


# ---------------------------------------------------------------------------
# BrandingConfig assembly
# ---------------------------------------------------------------------------


class TestBrandingAssembly:
    def test_uses_company_name(self):
        ctx = _ctx(company_name="AcmeCorp")
        branding = _build_branding(ctx)
        assert isinstance(branding, BrandingConfig)
        assert branding.company_name == "AcmeCorp"

    def test_empty_company_name(self):
        ctx = _ctx(company_name="")
        branding = _build_branding(ctx)
        assert branding.company_name == ""

    def test_defaults_preserved(self):
        ctx = _ctx()
        branding = _build_branding(ctx)
        assert branding.primary_color == "#00e87b"
        assert branding.font_family == "Inter, sans-serif"


# ---------------------------------------------------------------------------
# SocialProofConfig assembly
# ---------------------------------------------------------------------------


class TestSocialProofAssembly:
    def test_testimonial_creates_quote_proof(self):
        ctx = _ctx()
        proof = _build_social_proof(ctx)
        assert proof is not None
        assert proof.type == "quote"
        assert proof.quote_text == "Great product"
        assert proof.quote_author == "J"

    def test_logos_fallback_when_no_testimonials(self):
        ctx = _ctx(testimonials=[])
        proof = _build_social_proof(ctx)
        assert proof is not None
        assert proof.type == "logos"
        assert proof.logos == ["logo1.png", "logo2.png"]

    def test_none_when_no_data(self):
        ctx = _ctx(testimonials=[], customer_logos=[])
        proof = _build_social_proof(ctx)
        assert proof is None


# ---------------------------------------------------------------------------
# Generator dispatches correct output schema per template
# ---------------------------------------------------------------------------


class TestSchemaDispatch:
    @pytest.mark.asyncio
    async def test_lead_magnet_download_uses_correct_schema(self):
        mock = _mock_claude(_lead_magnet_page_output())
        gen = LandingPageGenerator()
        await gen.generate(mock, _ctx(), template_type="lead_magnet_download")
        schema = mock.generate_structured.call_args.kwargs["output_schema"]
        assert schema is LeadMagnetPageOutput

    @pytest.mark.asyncio
    async def test_case_study_uses_correct_schema(self):
        mock = _mock_claude(_case_study_page_output())
        gen = LandingPageGenerator()
        await gen.generate(mock, _ctx(), template_type="case_study")
        schema = mock.generate_structured.call_args.kwargs["output_schema"]
        assert schema is CaseStudyPageOutput

    @pytest.mark.asyncio
    async def test_webinar_uses_correct_schema(self):
        mock = _mock_claude(_webinar_page_output())
        gen = LandingPageGenerator()
        await gen.generate(mock, _ctx(), template_type="webinar")
        schema = mock.generate_structured.call_args.kwargs["output_schema"]
        assert schema is WebinarPageOutput

    @pytest.mark.asyncio
    async def test_demo_request_uses_correct_schema(self):
        mock = _mock_claude(_demo_request_page_output())
        gen = LandingPageGenerator()
        await gen.generate(mock, _ctx(), template_type="demo_request")
        schema = mock.generate_structured.call_args.kwargs["output_schema"]
        assert schema is DemoRequestPageOutput

    @pytest.mark.asyncio
    async def test_schema_restored_after_generate(self):
        mock = _mock_claude(_case_study_page_output())
        gen = LandingPageGenerator()
        original = gen.output_schema
        await gen.generate(mock, _ctx(), template_type="case_study")
        assert gen.output_schema is original

    @pytest.mark.asyncio
    async def test_unknown_template_in_generate_raises(self):
        mock = _mock_claude()
        gen = LandingPageGenerator()
        with pytest.raises(ValueError, match="Unknown landing page template"):
            await gen.generate(mock, _ctx(), template_type="nonexistent")


# ---------------------------------------------------------------------------
# End-to-end convenience function
# ---------------------------------------------------------------------------


class TestGenerateLandingPage:
    @pytest.mark.asyncio
    async def test_lead_magnet_download_returns_correct_type(self):
        mock = _mock_claude(_lead_magnet_page_output())
        result = await generate_landing_page(mock, _ctx(), template_type="lead_magnet_download")
        assert isinstance(result, LeadMagnetPageInput)

    @pytest.mark.asyncio
    async def test_case_study_returns_correct_type(self):
        mock = _mock_claude(_case_study_page_output())
        result = await generate_landing_page(mock, _ctx(), template_type="case_study")
        assert isinstance(result, CaseStudyPageInput)

    @pytest.mark.asyncio
    async def test_webinar_returns_correct_type(self):
        mock = _mock_claude(_webinar_page_output())
        result = await generate_landing_page(
            mock, _ctx(), template_type="webinar",
            event_date="2026-04-15", speakers=[{"name": "J"}],
        )
        assert isinstance(result, WebinarPageInput)
        assert result.event_date == "2026-04-15"

    @pytest.mark.asyncio
    async def test_demo_request_returns_correct_type(self):
        mock = _mock_claude(_demo_request_page_output())
        result = await generate_landing_page(mock, _ctx(), template_type="demo_request")
        assert isinstance(result, DemoRequestPageInput)


# ---------------------------------------------------------------------------
# Generator registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_registered_in_registry(self):
        from app.assets.prompts.base import GENERATOR_REGISTRY

        assert "landing_page" in GENERATOR_REGISTRY
        assert isinstance(GENERATOR_REGISTRY["landing_page"], LandingPageGenerator)

    def test_generator_class_attributes(self):
        gen = LandingPageGenerator()
        assert gen.asset_type == "landing_page"
        assert gen.model == "claude-opus-4-20250514"
        assert gen.temperature == 0.5
