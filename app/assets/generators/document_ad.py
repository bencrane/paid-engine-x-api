"""LinkedIn Document Ad (Carousel) content generator.

BJC-174: Three narrative patterns (problem_solution, listicle, data_story),
5-8 slides with character limits, output mapping to DocumentAdInput.
"""

from __future__ import annotations

import logging
from typing import Any

from app.assets.context import AssetContext
from app.assets.models import BrandingConfig, DocumentAdInput, Slide
from app.assets.prompts.base import PromptTemplate, register_generator
from app.assets.prompts.schemas import DocumentAdOutput
from app.integrations.claude_ai import ClaudeClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Narrative patterns
# ---------------------------------------------------------------------------

VALID_PATTERNS = {"problem_solution", "listicle", "data_story"}

_PATTERN_INSTRUCTIONS: dict[str, str] = {
    "problem_solution": (
        "NARRATIVE PATTERN: Problem → Solution → Proof\n\n"
        "Follow this exact narrative arc across 5-8 slides:\n"
        "1. Hook slide — provocative question or stat that stops the scroll\n"
        "2-3. Problem slides — describe the pain points your audience feels. "
        "Be specific and relatable.\n"
        "4-5. Solution slides — present the framework/approach that solves the problem. "
        "Focus on methodology, not feature lists.\n"
        "6-7. Proof slides — concrete stats, case study snippet, or customer result. "
        "Use real numbers ('3x ROI', '47% reduction') not vague claims.\n"
        "8. CTA slide — clear call to action with urgency.\n"
    ),
    "listicle": (
        "NARRATIVE PATTERN: Listicle — '5 Signs Your X Is Failing'\n\n"
        "Follow this exact narrative arc across 5-8 slides:\n"
        "1. Title slide — number + topic (e.g., '5 Signs Your Pipeline Is Leaking')\n"
        "2-6. One sign per slide — each with a punchy headline and a brief explanation. "
        "Make each sign recognisable and relatable.\n"
        "7. Summary/so-what slide — tie the signs together and name the consequence\n"
        "8. CTA slide — clear call to action.\n"
    ),
    "data_story": (
        "NARRATIVE PATTERN: Data Story\n\n"
        "Follow this exact narrative arc across 5-8 slides:\n"
        "1. Big stat hook — one jaw-dropping number that earns the swipe\n"
        "2-5. Supporting data points — each with context that makes the number meaningful. "
        "Use stat_callout for the number and body for the context.\n"
        "6-7. Implications / what to do — translate the data into action items\n"
        "8. CTA slide — clear call to action.\n"
    ),
}


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class DocumentAdGenerator(PromptTemplate):
    """Generator for LinkedIn Document Ad (Carousel) content."""

    asset_type = "document_ad"
    model = ClaudeClient.MODEL_QUALITY
    output_schema = DocumentAdOutput
    temperature = 0.5

    def build_asset_specific_instructions(self, ctx: AssetContext, **kwargs: Any) -> str:
        """Build carousel prompt instructions.

        Accepts ``pattern`` kwarg — one of problem_solution, listicle, data_story.
        """
        pattern: str = kwargs.get("pattern", "problem_solution")

        if pattern not in VALID_PATTERNS:
            raise ValueError(
                f"Unknown carousel pattern '{pattern}'. "
                f"Valid: {sorted(VALID_PATTERNS)}"
            )

        parts: list[str] = []

        # Task header
        parts.append(
            "TASK: Generate a LinkedIn Document Ad (carousel) with a compelling "
            "narrative arc that keeps the viewer swiping.\n"
        )

        # Pattern-specific structure
        parts.append(_PATTERN_INSTRUCTIONS[pattern])

        # Slide constraints
        parts.append(
            "SLIDE CONSTRAINTS:\n"
            "- Total slides: 5-8 (inclusive)\n"
            "- headline: max 50 characters — punchy, scannable\n"
            "- body: max 120 characters — supporting detail (null if not needed)\n"
            "- stat_callout: a specific number or metric (e.g., '3x', '47%', '$2M') — "
            "not vague ('significant', 'major'). Null if no stat on this slide.\n"
            "- stat_label: label for the stat (e.g., 'ROI increase'). "
            "Required when stat_callout is set.\n"
            "- The LAST slide MUST have is_cta_slide=True and a cta_text value\n"
            "- Only the last slide should have is_cta_slide=True\n"
        )

        # Aspect ratio guidance
        parts.append(
            "ASPECT RATIO:\n"
            "- Default: '1:1' (square) — works best for most carousels\n"
            "- Use '4:5' when slides need more vertical space for longer text\n"
            "- Choose based on the amount of text in the slides\n"
        )

        # Quality rules
        parts.append(
            "QUALITY RULES:\n"
            "- Each slide must advance the narrative — no filler slides\n"
            "- Headlines should be readable in 2 seconds at mobile size\n"
            "- Stats must be specific numbers, not vague qualifiers\n"
            "- The carousel must tell a coherent story from first to last slide\n"
            "- Hook slide determines whether the viewer swipes — make it count\n"
        )

        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Output → rendering mapping
# ---------------------------------------------------------------------------


def _build_branding(ctx: AssetContext) -> BrandingConfig:
    """Build BrandingConfig from AssetContext."""
    return BrandingConfig(company_name=ctx.company_name or "")


def map_output_to_document_ad_input(
    output: DocumentAdOutput,
    ctx: AssetContext,
) -> DocumentAdInput:
    """Map generation output to the rendering input model."""
    slides = [
        Slide(
            headline=s.headline,
            body=s.body,
            stat_callout=s.stat_callout,
            stat_label=s.stat_label,
            is_cta_slide=s.is_cta_slide,
            cta_text=s.cta_text,
        )
        for s in output.slides
    ]
    return DocumentAdInput(
        slides=slides,
        branding=_build_branding(ctx),
        aspect_ratio=output.aspect_ratio,
    )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


async def generate_document_ad(
    claude: ClaudeClient,
    ctx: AssetContext,
    pattern: str = "problem_solution",
) -> DocumentAdInput:
    """Generate a document ad carousel and return the rendering input."""
    if pattern not in VALID_PATTERNS:
        raise ValueError(
            f"Unknown carousel pattern '{pattern}'. "
            f"Valid: {sorted(VALID_PATTERNS)}"
        )
    generator = DocumentAdGenerator()
    output = await generator.generate(claude, ctx, pattern=pattern)
    return map_output_to_document_ad_input(output, ctx)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

register_generator(DocumentAdGenerator())
