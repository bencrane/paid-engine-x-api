"""Image concept brief content generator.

BJC-173: Platform-aware image briefs with dimensions, brand color palette,
anti-cliché guidance, and multi-platform convenience function.
"""

from __future__ import annotations

import logging
from typing import Any

from app.assets.context import AssetContext
from app.assets.prompts.base import PromptTemplate, register_generator
from app.assets.prompts.schemas import ImageBriefSetOutput
from app.integrations.claude_ai import ClaudeClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform / format dimensions
# ---------------------------------------------------------------------------

PLATFORM_DIMENSIONS: dict[str, dict[str, str]] = {
    "linkedin_sponsored": {
        "label": "LinkedIn Sponsored Content",
        "dimensions": "1200x628",
        "aspect_ratio": "1.91:1",
        "notes": "Landscape format. Text overlay must be large enough to read in-feed.",
    },
    "linkedin_carousel": {
        "label": "LinkedIn Carousel Card",
        "dimensions": "1080x1080",
        "aspect_ratio": "1:1",
        "notes": "Square cards. Keep key visuals centred — edges may be cropped on mobile.",
    },
    "meta_feed": {
        "label": "Meta Feed (Facebook / Instagram)",
        "dimensions": "1080x1080",
        "aspect_ratio": "1:1",
        "notes": "Square format optimised for mobile feed. Minimal text overlay (Meta 20% rule).",
    },
    "meta_story": {
        "label": "Meta Story / Reels",
        "dimensions": "1080x1920",
        "aspect_ratio": "9:16",
        "notes": "Full-screen vertical. Keep text in the safe zone (middle 80%).",
    },
    "landing_page_hero": {
        "label": "Landing Page Hero Image",
        "dimensions": "1920x1080",
        "aspect_ratio": "16:9",
        "notes": "Wide hero banner. Image should work with text overlay on left or right half.",
    },
}

VALID_PLATFORMS = set(PLATFORM_DIMENSIONS.keys())


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class ImageBriefGenerator(PromptTemplate):
    """Generator for image concept briefs."""

    asset_type = "image_brief"
    model = ClaudeClient.MODEL_FAST
    output_schema = ImageBriefSetOutput
    temperature = 0.6

    def build_asset_specific_instructions(self, ctx: AssetContext, **kwargs: Any) -> str:
        """Build image brief prompt instructions.

        Accepts ``platforms`` kwarg — a list of platform/format keys.
        """
        platforms: list[str] = kwargs.get("platforms", ["linkedin_sponsored"])

        parts: list[str] = []

        # Header
        parts.append(
            "TASK: Generate image concept briefs for the following platform/format "
            "combinations. Produce exactly 1 brief per platform.\n"
        )

        # Per-platform dimension blocks
        for platform in platforms:
            if platform not in PLATFORM_DIMENSIONS:
                raise ValueError(
                    f"Unknown image platform '{platform}'. "
                    f"Valid: {sorted(VALID_PLATFORMS)}"
                )
            info = PLATFORM_DIMENSIONS[platform]
            parts.append(
                f"PLATFORM: {info['label']}\n"
                f"- Dimensions: {info['dimensions']} ({info['aspect_ratio']})\n"
                f"- Notes: {info['notes']}\n"
            )

        # Brand color guidance
        brand_guidelines = getattr(ctx, "brand_guidelines", None) or {}
        if brand_guidelines:
            guidelines_text = "\n".join(
                f"  {k}: {v}" for k, v in brand_guidelines.items()
            )
            parts.append(
                f"BRAND GUIDELINES:\n{guidelines_text}\n\n"
                "Derive the color_palette for each brief from these brand guidelines. "
                "Use hex codes. Include 3-5 colours that reflect the brand.\n"
            )
        else:
            parts.append(
                "BRAND COLORS: No brand guidelines provided. "
                "Choose a cohesive, professional colour palette (3-5 hex codes) "
                "that suits the industry and objective.\n"
            )

        # Visual description quality rules
        parts.append(
            "VISUAL DESCRIPTION RULES:\n"
            "- Be SPECIFIC. Describe the exact scene, subjects, composition, and lighting.\n"
            "- BAD: 'A professional image showing teamwork'\n"
            "- GOOD: 'Overhead shot of four people around a whiteboard covered in sticky "
            "notes, warm natural light from a floor-to-ceiling window on the left, "
            "shallow depth of field focusing on the hands placing a yellow sticky note'\n"
            "- Include camera angle, lighting direction, depth of field, colour temperature\n"
            "- Reference a concrete art style or photographic technique (e.g., "
            "'flat-lay product photography', 'isometric 3D illustration', 'editorial "
            "portrait with Rembrandt lighting')\n"
        )

        # Anti-cliché / do_not_include guidance
        parts.append(
            "DO NOT INCLUDE (anti-cliché list):\n"
            "Populate the do_not_include field with stock-photo clichés to avoid. "
            "Always include at least these:\n"
            "- Handshake photos\n"
            "- Generic office/meeting room scenes with no context\n"
            "- Overly posed group shots with forced smiles\n"
            "- Floating holographic UI screens\n"
            "- Abstract puzzle pieces or gears representing 'teamwork'\n"
            "Add any additional clichés specific to the industry or use case.\n"
        )

        # Mood and style
        parts.append(
            "MOOD & STYLE:\n"
            "- mood: one concise phrase (e.g., 'confident and forward-looking')\n"
            "- style_reference: reference a specific visual style, artist, or technique "
            "(e.g., 'Apple product photography', 'Dieter Rams minimalism', "
            "'National Geographic editorial')\n"
        )

        # Text overlay
        parts.append(
            "TEXT OVERLAY:\n"
            "- If the ad format typically includes text overlay, provide short, punchy copy\n"
            "- If the format does not use text overlay (e.g., landing page hero where "
            "text is in HTML), set text_overlay to null\n"
        )

        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


async def generate_image_briefs(
    claude: ClaudeClient,
    ctx: AssetContext,
    platforms: list[str] | None = None,
) -> ImageBriefSetOutput:
    """Generate image concept briefs for the given platforms."""
    platforms = platforms or ["linkedin_sponsored"]
    for p in platforms:
        if p not in VALID_PLATFORMS:
            raise ValueError(
                f"Unknown image platform '{p}'. Valid: {sorted(VALID_PLATFORMS)}"
            )
    generator = ImageBriefGenerator()
    result = await generator.generate(claude, ctx, platforms=platforms)
    return result  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

register_generator(ImageBriefGenerator())
