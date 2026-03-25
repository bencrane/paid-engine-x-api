"""Tests for BJC-175: Video script content generator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assets.context import AssetContext
from app.assets.generators.video_script import (
    VALID_DURATIONS,
    VALID_PLATFORMS,
    VideoScriptGenerator,
    generate_video_script,
)
from app.assets.prompts.schemas import ScriptSegment, VideoScriptOutput


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


def _segment(
    start: str = "0:00",
    end: str = "0:03",
    spoken: str = "Is your team audit-ready?",
    visual: str = "Close-up of a laptop screen showing a compliance dashboard",
    overlay: str | None = "Are You Audit-Ready?",
    caption: str = "Is your team audit-ready?",
) -> ScriptSegment:
    return ScriptSegment(
        timestamp_start=start,
        timestamp_end=end,
        spoken_text=spoken,
        visual_direction=visual,
        text_overlay=overlay,
        caption_text=caption,
    )


def _video_output_30s() -> VideoScriptOutput:
    return VideoScriptOutput(
        title="TestCo Compliance in 30 Seconds",
        duration="30s",
        aspect_ratio="4:5",
        hook=_segment("0:00", "0:03"),
        body=[
            _segment("0:03", "0:10", "Compliance audits drain weeks.", "Wide shot of team at desks", None, "Compliance audits drain weeks."),
            _segment("0:10", "0:20", "TestCo automates the busywork.", "Screen recording of TestCo dashboard", "Automate Compliance", "TestCo automates the busywork."),
        ],
        cta=_segment("0:20", "0:30", "Start your free trial today.", "Logo with URL", "Start Free Trial", "Start your free trial today."),
        total_word_count=72,
        music_direction="Upbeat electronic, 120 BPM, builds to crescendo at CTA",
        target_platform="linkedin",
    )


def _video_output_60s() -> VideoScriptOutput:
    return VideoScriptOutput(
        title="TestCo Compliance Deep Dive",
        duration="60s",
        aspect_ratio="16:9",
        hook=_segment("0:00", "0:03"),
        body=[
            _segment("0:03", "0:15", "Every quarter, your team scrambles.", "Montage of stressed workers", None, "Every quarter, your team scrambles."),
            _segment("0:15", "0:35", "TestCo connects to your stack and monitors continuously.", "Screen recording walkthrough", "Continuous Monitoring", "TestCo connects to your stack."),
            _segment("0:35", "0:50", "BigCo cut audit prep by 40%.", "Customer quote card", "40% Faster", "BigCo cut audit prep by 40%."),
        ],
        cta=_segment("0:50", "1:00", "Book a 15-minute demo.", "Logo + calendar link", "Book a Demo", "Book a 15-minute demo."),
        total_word_count=145,
        music_direction="Ambient corporate, slow build, confident tone",
        target_platform="youtube",
    )


def _mock_claude(return_value: Any = None) -> MagicMock:
    mock = MagicMock()
    mock.generate_structured = AsyncMock(
        return_value=return_value or _video_output_30s()
    )
    return mock


# ---------------------------------------------------------------------------
# Duration structure tests
# ---------------------------------------------------------------------------


class TestDurationStructure:
    def _get_instructions(self, duration: str = "30s", platform: str = "linkedin") -> str:
        gen = VideoScriptGenerator()
        return gen.build_asset_specific_instructions(_ctx(), duration=duration, platform=platform)

    def test_30s_structure(self):
        text = self._get_instructions("30s")
        assert "30 seconds" in text
        assert "75 words" in text or "~75" in text
        assert "Hook" in text
        assert "Problem" in text
        assert "Solution" in text
        assert "CTA" in text

    def test_60s_structure(self):
        text = self._get_instructions("60s")
        assert "60 seconds" in text
        assert "150 words" in text or "~150" in text
        assert "Proof" in text  # 60s has extra Proof segment

    def test_30s_timestamps(self):
        text = self._get_instructions("30s")
        assert "0:00" in text
        assert "0:03" in text
        assert "0:10" in text
        assert "0:20" in text
        assert "0:30" in text

    def test_60s_timestamps(self):
        text = self._get_instructions("60s")
        assert "0:00" in text
        assert "0:15" in text
        assert "0:35" in text
        assert "0:50" in text
        assert "1:00" in text

    def test_unknown_duration_raises(self):
        gen = VideoScriptGenerator()
        with pytest.raises(ValueError, match="Unknown duration"):
            gen.build_asset_specific_instructions(_ctx(), duration="45s")


# ---------------------------------------------------------------------------
# Platform guidance tests
# ---------------------------------------------------------------------------


class TestPlatformGuidance:
    def _get_instructions(self, platform: str) -> str:
        gen = VideoScriptGenerator()
        return gen.build_asset_specific_instructions(_ctx(), duration="30s", platform=platform)

    def test_linkedin_guidance(self):
        text = self._get_instructions("linkedin")
        assert "LinkedIn" in text
        assert "4:5" in text
        assert "caption" in text.lower()

    def test_meta_guidance(self):
        text = self._get_instructions("meta")
        assert "Meta" in text
        assert "scroll" in text.lower() or "Reels" in text

    def test_youtube_guidance(self):
        text = self._get_instructions("youtube")
        assert "YouTube" in text
        assert "16:9" in text
        assert "educational" in text.lower() or "value" in text.lower()

    def test_unknown_platform_raises(self):
        gen = VideoScriptGenerator()
        with pytest.raises(ValueError, match="Unknown video platform"):
            gen.build_asset_specific_instructions(_ctx(), duration="30s", platform="tiktok")

    def test_default_duration_and_platform(self):
        gen = VideoScriptGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "30 seconds" in text
        assert "LinkedIn" in text


# ---------------------------------------------------------------------------
# Aspect ratio tests
# ---------------------------------------------------------------------------


class TestAspectRatio:
    def test_linkedin_aspect_ratio(self):
        gen = VideoScriptGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), platform="linkedin")
        assert "'4:5'" in text

    def test_meta_aspect_ratio(self):
        gen = VideoScriptGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), platform="meta")
        assert "'4:5'" in text

    def test_youtube_aspect_ratio(self):
        gen = VideoScriptGenerator()
        text = gen.build_asset_specific_instructions(_ctx(), platform="youtube")
        assert "'16:9'" in text


# ---------------------------------------------------------------------------
# Segment rules
# ---------------------------------------------------------------------------


class TestSegmentRules:
    def test_contains_timestamp_format(self):
        gen = VideoScriptGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "M:SS" in text

    def test_contains_spoken_text_rule(self):
        gen = VideoScriptGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "spoken_text" in text

    def test_contains_visual_direction_rule(self):
        gen = VideoScriptGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "visual_direction" in text

    def test_contains_caption_rule(self):
        gen = VideoScriptGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "caption_text" in text

    def test_contains_music_direction(self):
        gen = VideoScriptGenerator()
        text = gen.build_asset_specific_instructions(_ctx())
        assert "music" in text.lower()

    def test_contains_word_count_target(self):
        gen = VideoScriptGenerator()
        text_30 = gen.build_asset_specific_instructions(_ctx(), duration="30s")
        text_60 = gen.build_asset_specific_instructions(_ctx(), duration="60s")
        assert "75" in text_30
        assert "150" in text_60


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


class TestGenerateVideoScript:
    @pytest.mark.asyncio
    async def test_returns_video_script_output(self):
        mock = _mock_claude()
        result = await generate_video_script(mock, _ctx())
        assert isinstance(result, VideoScriptOutput)
        assert result.duration == "30s"

    @pytest.mark.asyncio
    async def test_60s_script(self):
        mock = _mock_claude(_video_output_60s())
        result = await generate_video_script(mock, _ctx(), duration="60s", platform="youtube")
        assert result.duration == "60s"
        assert len(result.body) == 3  # problem, solution, proof

    @pytest.mark.asyncio
    async def test_passes_kwargs_to_generator(self):
        mock = _mock_claude()
        await generate_video_script(mock, _ctx(), duration="30s", platform="meta")
        call_kwargs = mock.generate_structured.call_args.kwargs
        assert "Meta" in call_kwargs["user_prompt"]
        assert "30 seconds" in call_kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_invalid_duration_raises(self):
        mock = _mock_claude()
        with pytest.raises(ValueError, match="Unknown duration"):
            await generate_video_script(mock, _ctx(), duration="45s")

    @pytest.mark.asyncio
    async def test_invalid_platform_raises(self):
        mock = _mock_claude()
        with pytest.raises(ValueError, match="Unknown video platform"):
            await generate_video_script(mock, _ctx(), platform="tiktok")


# ---------------------------------------------------------------------------
# Registration and attributes
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_registered_in_registry(self):
        from app.assets.prompts.base import GENERATOR_REGISTRY, register_generator
        # Re-register in case another test cleared the registry
        register_generator(VideoScriptGenerator())
        assert "video_script" in GENERATOR_REGISTRY
        assert isinstance(GENERATOR_REGISTRY["video_script"], VideoScriptGenerator)

    def test_generator_attributes(self):
        gen = VideoScriptGenerator()
        assert gen.asset_type == "video_script"
        assert gen.model == "claude-sonnet-4-20250514"
        assert gen.output_schema is VideoScriptOutput
        assert gen.temperature == 0.5

    def test_does_not_need_social_proof(self):
        gen = VideoScriptGenerator()
        assert gen._needs_social_proof() is False
