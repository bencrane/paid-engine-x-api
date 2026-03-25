"""Tests for BJC-172: Email nurture sequence content generator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assets.context import AssetContext
from app.assets.generators.email_copy import (
    VALID_TRIGGERS,
    EmailCopyGenerator,
    generate_email_sequence,
)
from app.assets.prompts.schemas import EmailSequenceOutput, NurtureEmail


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


def _email_sequence_output(trigger: str = "lead_magnet_download") -> EmailSequenceOutput:
    return EmailSequenceOutput(
        sequence_name="TestCo Compliance Nurture",
        trigger=trigger,
        emails=[
            NurtureEmail(
                subject_line="Your compliance checklist is here",
                preview_text="Plus one insight most teams miss",
                body_html="<p>Hi {{first_name}},</p><p>Thanks for downloading.</p>",
                send_delay_days=0,
                purpose="value_delivery",
            ),
            NurtureEmail(
                subject_line="The #1 compliance mistake we see",
                preview_text="And how {{company}} can avoid it",
                body_html="<p>Hi {{first_name}},</p><p>Here is an insight.</p>",
                send_delay_days=2,
                purpose="education",
            ),
            NurtureEmail(
                subject_line="How BigCo cut audit prep by 40%",
                preview_text="Real results from a team like yours",
                body_html="<p>Hi {{first_name}},</p><p>BigCo reduced prep time.</p>",
                send_delay_days=5,
                purpose="social_proof",
            ),
            NurtureEmail(
                subject_line="Teams like {{company}} use TestCo",
                preview_text="See how they simplified compliance",
                body_html="<p>Hi {{first_name}},</p><p>Companies like yours.</p>",
                send_delay_days=8,
                purpose="soft_pitch",
            ),
            NurtureEmail(
                subject_line="Quick question about compliance",
                preview_text="15 minutes could save you 40 hours",
                body_html="<p>Hi {{first_name}},</p><p>Book a demo.</p>",
                send_delay_days=12,
                purpose="direct_cta",
            ),
        ],
    )


def _mock_claude(return_value: Any = None) -> MagicMock:
    mock = MagicMock()
    mock.generate_structured = AsyncMock(
        return_value=return_value or _email_sequence_output()
    )
    return mock


# ---------------------------------------------------------------------------
# Prompt structure tests
# ---------------------------------------------------------------------------


class TestPromptStructure:
    def _get_instructions(self, trigger: str = "lead_magnet_download") -> str:
        gen = EmailCopyGenerator()
        return gen.build_asset_specific_instructions(_ctx(), trigger=trigger)

    def test_contains_progressive_disclosure(self):
        text = self._get_instructions()
        assert "value_delivery" in text
        assert "education" in text
        assert "social_proof" in text
        assert "soft_pitch" in text
        assert "direct_cta" in text

    def test_contains_day_progression(self):
        text = self._get_instructions()
        assert "Day 0" in text
        assert "Day 2" in text
        assert "Day 5" in text
        assert "Day 8" in text
        assert "Day 12" in text

    def test_contains_personalization_tokens(self):
        text = self._get_instructions()
        assert "{{first_name}}" in text
        assert "{{company}}" in text

    def test_contains_subject_line_constraints(self):
        text = self._get_instructions()
        assert "60 characters" in text or "60 char" in text.lower()
        assert "spam" in text.lower()
        assert "ALL CAPS" in text

    def test_contains_preview_text_constraints(self):
        text = self._get_instructions()
        assert "90 characters" in text or "90 char" in text.lower()

    def test_contains_single_cta_rule(self):
        text = self._get_instructions()
        assert "single CTA" in text or "single cta" in text.lower()


# ---------------------------------------------------------------------------
# Trigger-specific prompt customization
# ---------------------------------------------------------------------------


class TestTriggerTypes:
    def test_lead_magnet_download_trigger(self):
        gen = EmailCopyGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), trigger="lead_magnet_download")
        assert "Lead Magnet Download" in text
        assert "downloaded" in text.lower() or "download" in text.lower()

    def test_webinar_registration_trigger(self):
        gen = EmailCopyGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), trigger="webinar_registration")
        assert "Webinar Registration" in text
        assert "webinar" in text.lower()

    def test_demo_request_trigger(self):
        gen = EmailCopyGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), trigger="demo_request")
        assert "Demo Request" in text
        assert "high-intent" in text.lower() or "bottom-of-funnel" in text.lower()

    def test_default_trigger_is_lead_magnet(self):
        gen = EmailCopyGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "Lead Magnet Download" in text


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


class TestGenerateEmailSequence:
    @pytest.mark.asyncio
    async def test_returns_email_sequence_output(self):
        mock = _mock_claude()
        result = await generate_email_sequence(mock, _ctx())
        assert isinstance(result, EmailSequenceOutput)
        assert len(result.emails) == 5

    @pytest.mark.asyncio
    async def test_passes_trigger_to_generator(self):
        mock = _mock_claude(_email_sequence_output("webinar_registration"))
        result = await generate_email_sequence(
            mock, _ctx(), trigger="webinar_registration"
        )
        # The trigger kwarg is passed through to build_asset_specific_instructions
        call_kwargs = mock.generate_structured.call_args.kwargs
        assert "webinar" in call_kwargs["user_prompt"].lower()

    @pytest.mark.asyncio
    async def test_invalid_trigger_raises(self):
        mock = _mock_claude()
        with pytest.raises(ValueError, match="Unknown trigger"):
            await generate_email_sequence(mock, _ctx(), trigger="invalid_trigger")


# ---------------------------------------------------------------------------
# Registration and attributes
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_registered_in_registry(self):
        from app.assets.prompts.base import GENERATOR_REGISTRY
        assert "email_copy" in GENERATOR_REGISTRY
        assert isinstance(GENERATOR_REGISTRY["email_copy"], EmailCopyGenerator)

    def test_generator_attributes(self):
        gen = EmailCopyGenerator()
        assert gen.asset_type == "email_copy"
        assert gen.model == "claude-sonnet-4-20250514"
        assert gen.output_schema is EmailSequenceOutput
        assert gen.temperature == 0.5

    def test_does_not_need_social_proof(self):
        gen = EmailCopyGenerator()
        assert gen._needs_social_proof() is False
