"""Ad copy content generator.

BJC-171: Multi-platform ad copy (LinkedIn, Meta, Google RSA) with strict
character limits, per-platform schemas, and post-generation validation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel

from app.assets.context import AssetContext
from app.assets.prompts.base import PromptTemplate, register_generator
from app.assets.prompts.schemas import (
    AdCopyOutput,
    GoogleRSACopyOutput,
    LinkedInAdCopyOutput,
    LinkedInAdCopyVariant,
    MetaAdCopyOutput,
    MetaAdCopyVariant,
)
from app.integrations.claude_ai import ClaudeClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform config
# ---------------------------------------------------------------------------

VALID_PLATFORMS = {"linkedin", "meta", "google"}

_OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "linkedin": LinkedInAdCopyOutput,
    "meta": MetaAdCopyOutput,
    "google": GoogleRSACopyOutput,
}

# Character limits: {platform: {field: max_chars}}
CHAR_LIMITS: dict[str, dict[str, int]] = {
    "linkedin": {
        "introductory_text": 600,
        "headline": 70,
        "description": 100,
    },
    "meta": {
        "primary_text": 125,
        "headline": 40,
        "description": 30,
    },
    "google": {
        "headlines": 30,
        "descriptions": 90,
        "path1": 15,
        "path2": 15,
    },
}

LINKEDIN_CTAS = {
    "Apply", "Download", "Get Quote", "Learn More", "Sign Up",
    "Subscribe", "Register", "Join", "Attend", "Request Demo",
}

META_CTAS = {
    "LEARN_MORE", "SIGN_UP", "DOWNLOAD", "GET_QUOTE",
    "CONTACT_US", "APPLY_NOW", "SUBSCRIBE", "BOOK_NOW",
}


# ---------------------------------------------------------------------------
# Character limit validation
# ---------------------------------------------------------------------------


def _truncate_at_word_boundary(text: str, max_chars: int) -> str:
    """Truncate text at word boundary, respecting max_chars."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Find last space to avoid mid-word cut
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated


def validate_ad_copy_limits(
    platform: str, output: BaseModel,
) -> tuple[BaseModel, list[str]]:
    """Validate and fix character limits. Returns (fixed_output, warnings)."""
    warnings: list[str] = []
    limits = CHAR_LIMITS.get(platform, {})

    if platform == "linkedin" and isinstance(output, LinkedInAdCopyOutput):
        for i, v in enumerate(output.variants):
            for field_name in ("introductory_text", "headline", "description"):
                limit = limits[field_name]
                val = getattr(v, field_name)
                if len(val) > limit:
                    fixed = _truncate_at_word_boundary(val, limit)
                    warnings.append(
                        f"linkedin variant {i} {field_name}: {len(val)} chars "
                        f"→ truncated to {len(fixed)} (limit {limit})"
                    )
                    object.__setattr__(v, field_name, fixed)

    elif platform == "meta" and isinstance(output, MetaAdCopyOutput):
        for i, v in enumerate(output.variants):
            for field_name in ("primary_text", "headline", "description"):
                limit = limits[field_name]
                val = getattr(v, field_name)
                if len(val) > limit:
                    fixed = _truncate_at_word_boundary(val, limit)
                    warnings.append(
                        f"meta variant {i} {field_name}: {len(val)} chars "
                        f"→ truncated to {len(fixed)} (limit {limit})"
                    )
                    object.__setattr__(v, field_name, fixed)

    elif platform == "google" and isinstance(output, GoogleRSACopyOutput):
        for i, h in enumerate(output.headlines):
            if len(h) > limits["headlines"]:
                fixed = _truncate_at_word_boundary(h, limits["headlines"])
                warnings.append(
                    f"google headline {i}: {len(h)} chars "
                    f"→ truncated to {len(fixed)} (limit {limits['headlines']})"
                )
                output.headlines[i] = fixed
        for i, d in enumerate(output.descriptions):
            if len(d) > limits["descriptions"]:
                fixed = _truncate_at_word_boundary(d, limits["descriptions"])
                warnings.append(
                    f"google description {i}: {len(d)} chars "
                    f"→ truncated to {len(fixed)} (limit {limits['descriptions']})"
                )
                output.descriptions[i] = fixed
        if len(output.path1) > limits["path1"]:
            fixed = _truncate_at_word_boundary(output.path1, limits["path1"])
            warnings.append(f"google path1: truncated to {len(fixed)}")
            output.path1 = fixed
        if len(output.path2) > limits["path2"]:
            fixed = _truncate_at_word_boundary(output.path2, limits["path2"])
            warnings.append(f"google path2: truncated to {len(fixed)}")
            output.path2 = fixed

    if warnings:
        for w in warnings:
            logger.warning("ad_copy_limit_exceeded: %s", w)

    return output, warnings


# ---------------------------------------------------------------------------
# Platform-specific prompt instructions
# ---------------------------------------------------------------------------


def _linkedin_instructions(ctx: AssetContext) -> str:
    return (
        "PLATFORM: LINKEDIN SPONSORED CONTENT\n\n"
        "Generate exactly 3 ad copy variants for LinkedIn Sponsored Content.\n\n"
        "CHARACTER LIMITS (strict — do not exceed):\n"
        "- introductory_text: max 600 characters. The first 150 characters appear "
        "before the 'see more' fold — front-load the hook.\n"
        "- headline: max 70 characters. Benefit-driven, not feature-driven. "
        "Use specific outcomes and numbers.\n"
        "- description: max 100 characters. Supporting context or proof point.\n"
        "- cta: Choose from: Apply, Download, Get Quote, Learn More, Sign Up, "
        "Subscribe, Register, Join, Attend, Request Demo.\n\n"
        "VARIANT STRATEGY:\n"
        "- Variant 1: Problem-agitation — name the pain directly\n"
        "- Variant 2: Social proof — lead with a result or customer outcome\n"
        "- Variant 3: Curiosity — ask a question or tease an insight\n\n"
        "RULES:\n"
        "- Professional B2B tone appropriate for LinkedIn\n"
        "- Each variant must be distinct in approach, not just rewording\n"
        "- Front-load value in the first 150 chars of introductory_text\n"
        "- Use concrete numbers and specific outcomes, not vague promises\n"
        "- No clickbait, no ALL CAPS, no excessive punctuation\n"
    )


def _meta_instructions(ctx: AssetContext) -> str:
    return (
        "PLATFORM: META (FACEBOOK / INSTAGRAM)\n\n"
        "Generate exactly 3 ad copy variants for Meta (Facebook/Instagram) ads.\n\n"
        "CHARACTER LIMITS (strict — do not exceed):\n"
        "- primary_text: max 125 characters recommended (gets cut off on mobile)\n"
        "- headline: max 40 characters. Punchy, scroll-stopping.\n"
        "- description: max 30 characters. Brief supporting text.\n"
        "- cta: Choose from: LEARN_MORE, SIGN_UP, DOWNLOAD, GET_QUOTE, "
        "CONTACT_US, APPLY_NOW, SUBSCRIBE, BOOK_NOW.\n\n"
        "VARIANT STRATEGY:\n"
        "- Variant 1: Outcome-focused — lead with the transformation\n"
        "- Variant 2: Question hook — ask something the audience cares about\n"
        "- Variant 3: Stat/proof — lead with a compelling number\n\n"
        "RULES:\n"
        "- Shorter is better — users scroll fast on Meta\n"
        "- Conversational but professional tone\n"
        "- Each variant must be distinct in approach\n"
        "- Use emojis sparingly (max 1 per variant, only if appropriate for brand)\n"
        "- Avoid B2B jargon — write like a human, not a brochure\n"
    )


def _google_instructions(ctx: AssetContext) -> str:
    return (
        "PLATFORM: GOOGLE RESPONSIVE SEARCH AD (RSA)\n\n"
        "Generate a complete RSA ad asset set.\n\n"
        "CHARACTER LIMITS (strict — do not exceed):\n"
        "- headlines: 15 headlines, each max 30 characters\n"
        "- descriptions: 4 descriptions, each max 90 characters\n"
        "- path1: max 15 characters (URL display path segment 1)\n"
        "- path2: max 15 characters (URL display path segment 2)\n\n"
        "HEADLINE REQUIREMENTS:\n"
        "- Each headline must be self-contained (any combination must work)\n"
        "- At least 1 headline with a specific number or statistic\n"
        "- At least 1 headline as a question\n"
        "- Include the company name in at least 1 headline\n"
        "- Mix: benefit headlines, feature headlines, CTA headlines, social proof\n"
        "- No duplicate meanings — each headline adds unique value\n\n"
        "DESCRIPTION REQUIREMENTS:\n"
        "- Each description should work independently\n"
        "- Include a clear CTA in at least 1 description\n"
        "- Mix benefit-driven and proof-driven descriptions\n\n"
        "PIN RECOMMENDATIONS:\n"
        "- First 3 headlines are best for pinning to Position 1 (most visible)\n"
        "- Put the strongest brand/benefit headline first\n\n"
        "RULES:\n"
        "- Every character counts — no filler words\n"
        "- Use title case for headlines\n"
        "- path1/path2 should be short, keyword-rich URL segments\n"
        "- No exclamation marks in headlines (Google policy)\n"
    )


_PLATFORM_BUILDERS: dict[str, Any] = {
    "linkedin": _linkedin_instructions,
    "meta": _meta_instructions,
    "google": _google_instructions,
}


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class AdCopyGenerator(PromptTemplate):
    """Generator for multi-platform ad copy."""

    asset_type = "ad_copy"
    model = ClaudeClient.MODEL_FAST
    output_schema = LinkedInAdCopyOutput  # default; overridden per platform
    temperature = 0.5

    def build_asset_specific_instructions(self, ctx: AssetContext, **kwargs: Any) -> str:
        """Build platform-specific prompt instructions.

        Accepts ``platform`` kwarg to select the ad platform.
        """
        platform = kwargs.get("platform", "linkedin")
        if platform not in _PLATFORM_BUILDERS:
            raise ValueError(
                f"Unknown ad platform '{platform}'. Valid: {sorted(VALID_PLATFORMS)}"
            )
        builder = _PLATFORM_BUILDERS[platform]
        return builder(ctx)

    async def generate(
        self,
        claude: ClaudeClient,
        ctx: AssetContext,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate ad copy with the correct output schema per platform."""
        platform = kwargs.get("platform", "linkedin")
        if platform not in _OUTPUT_SCHEMAS:
            raise ValueError(
                f"Unknown ad platform '{platform}'. Valid: {sorted(VALID_PLATFORMS)}"
            )

        original_schema = self.output_schema
        self.output_schema = _OUTPUT_SCHEMAS[platform]
        try:
            result = await super().generate(claude, ctx, **kwargs)
            validated, warnings = validate_ad_copy_limits(platform, result)
            return validated
        finally:
            self.output_schema = original_schema


# ---------------------------------------------------------------------------
# Multi-platform convenience function
# ---------------------------------------------------------------------------


async def generate_ad_copy(
    claude: ClaudeClient, ctx: AssetContext, platforms: list[str],
) -> dict[str, BaseModel]:
    """Generate ad copy for each requested platform.

    Runs platform generations in parallel with asyncio.gather.
    Returns {"linkedin": LinkedInAdCopyOutput, "meta": MetaAdCopyOutput, ...}
    """
    for p in platforms:
        if p not in VALID_PLATFORMS:
            raise ValueError(
                f"Unknown ad platform '{p}'. Valid: {sorted(VALID_PLATFORMS)}"
            )

    generator = AdCopyGenerator()

    async def _gen_one(platform: str) -> tuple[str, BaseModel]:
        result = await generator.generate(claude, ctx, platform=platform)
        return platform, result

    results = await asyncio.gather(*[_gen_one(p) for p in platforms])
    return dict(results)


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

register_generator(AdCopyGenerator())
