"""Case study page content generator.

BJC-176: Transforms raw case study data into polished marketing copy with
4 narrative sections, metric callouts, quote formatting, and BrandingConfig.
"""

from __future__ import annotations

import logging
from typing import Any

from app.assets.context import AssetContext
from app.assets.models import BrandingConfig, CaseStudyPageInput, MetricCallout, Section
from app.assets.prompts.base import PromptTemplate, register_generator
from app.assets.prompts.schemas import CaseStudyContentOutput
from app.integrations.claude_ai import ClaudeClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Narrative section names
# ---------------------------------------------------------------------------

NARRATIVE_SECTIONS = ("situation", "challenge", "solution", "results")


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class CaseStudyPageGenerator(PromptTemplate):
    """Generator for case study page content."""

    asset_type = "case_study_page"
    model = ClaudeClient.MODEL_QUALITY
    output_schema = CaseStudyContentOutput
    temperature = 0.6

    def build_asset_specific_instructions(self, ctx: AssetContext, **kwargs: Any) -> str:
        """Build case study prompt instructions.

        Accepts ``case_study_index`` kwarg — index into ctx.case_studies.
        """
        case_study_index: int = kwargs.get("case_study_index", 0)

        parts: list[str] = []

        # Task header
        parts.append(
            "TASK: Generate a compelling B2B case study page that turns raw data "
            "into a persuasive narrative.\n"
        )

        # Inject the specific case study data
        case_study = _get_case_study(ctx, case_study_index)
        if case_study:
            parts.append(_format_case_study_input(case_study))
        else:
            parts.append(
                "CASE STUDY DATA: No case study data available. "
                "Generate a compelling case study based on the company context and "
                "target persona. Use plausible but clearly marked placeholder data.\n"
            )

        # Headline guidance
        parts.append(
            "HEADLINE:\n"
            "- Format: 'How [Customer] achieved [Key Result]'\n"
            "- Must be specific and compelling\n"
            "- Include the actual result (e.g., 'How BigCo cut audit prep by 40%')\n"
            "- Avoid generic headlines like 'A Success Story'\n"
        )

        # Narrative structure
        parts.append(
            "NARRATIVE SECTIONS: Generate exactly 4 sections in this order:\n\n"
            "1. SITUATION — Set the scene\n"
            "   - Company context, industry, size, goals\n"
            "   - What they were trying to achieve\n"
            "   - 200-400 words, optional bullets for key facts\n\n"
            "2. CHALLENGE — Specific, relatable pain points\n"
            "   - What was blocking them\n"
            "   - Impact of the status quo (cost, time, risk)\n"
            "   - 200-400 words, optional bullets for pain points\n\n"
            "3. SOLUTION — How the product was used\n"
            "   - Specific features, approach, timeline\n"
            "   - Implementation story (not a feature list)\n"
            "   - 200-400 words, optional bullets for key steps\n\n"
            "4. RESULTS — Quantified outcomes WITH context\n"
            "   - Always pair numbers with context: '$2.1M pipeline in 90 days' "
            "not just '$2.1M'\n"
            "   - Before/after comparisons when possible\n"
            "   - 200-400 words, optional bullets for metrics\n"
        )

        # Metrics
        parts.append(
            "METRICS:\n"
            "- Extract 2-4 key metrics from the results data\n"
            "- Each metric has a 'value' (e.g., '3x', '47%', '$2.1M') "
            "and a 'label' (e.g., 'ROI increase', 'time saved')\n"
            "- Use specific numbers, not vague qualifiers\n"
            "- If exact numbers aren't in the source data, derive reasonable "
            "metrics from the available results\n"
        )

        # Quote handling
        parts.append(
            "QUOTE:\n"
            "- If a customer quote is available in the source data, include it\n"
            "- Set quote_text, quote_author, quote_title\n"
            "- If no quote is available, set all quote fields to null\n"
            "- Do NOT fabricate quotes\n"
        )

        # CTA
        parts.append(
            "CTA:\n"
            "- Contextual call-to-action text\n"
            "- Examples: 'Get Similar Results', 'See How We Can Help Your Team', "
            "'Start Your Transformation'\n"
            "- Must relate to the results shown in the case study\n"
        )

        # Writing quality
        parts.append(
            "WRITING RULES:\n"
            "- Third person narrative throughout\n"
            "- Weave direct customer quotes into the narrative where available\n"
            "- Be specific — avoid 'significant improvement' when you can say "
            "'47% reduction in audit prep time'\n"
            "- Each section should flow naturally into the next\n"
        )

        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_case_study(ctx: AssetContext, index: int) -> dict | None:
    """Safely get a case study from context by index."""
    if not ctx.case_studies or index >= len(ctx.case_studies):
        return None
    return ctx.case_studies[index]


def _format_case_study_input(cs: dict) -> str:
    """Format raw case study data for prompt injection."""
    lines = ["SOURCE CASE STUDY DATA:"]

    name = cs.get("customer_name", "Unknown Customer")
    lines.append(f"  Customer: {name}")

    for field in ("customer_industry", "company_size", "problem", "solution"):
        val = cs.get(field)
        if val:
            label = field.replace("_", " ").title()
            lines.append(f"  {label}: {val}")

    results = cs.get("results")
    if results:
        if isinstance(results, dict):
            metrics = ", ".join(f"{k}: {v}" for k, v in results.items())
            lines.append(f"  Results: {metrics}")
        else:
            lines.append(f"  Results: {results}")

    quote = cs.get("quote")
    if quote and isinstance(quote, dict):
        q_text = quote.get("text", "")
        q_author = quote.get("author", "")
        q_title = quote.get("title", "")
        if q_text:
            lines.append(f'  Quote: "{q_text}" — {q_author}, {q_title}')
    elif quote and isinstance(quote, str):
        lines.append(f'  Quote: "{quote}"')

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output → rendering mapping
# ---------------------------------------------------------------------------


def _build_branding(ctx: AssetContext) -> BrandingConfig:
    """Build BrandingConfig from AssetContext."""
    return BrandingConfig(company_name=ctx.company_name or "")


def map_output_to_case_study_page_input(
    output: CaseStudyContentOutput,
    ctx: AssetContext,
    case_study_index: int = 0,
) -> CaseStudyPageInput:
    """Map generation output to the rendering input model."""
    # Map sections
    sections = [
        Section(
            heading=s.heading,
            body=s.body,
            bullets=s.bullets,
        )
        for s in output.sections
    ]

    # Map metrics
    metrics = [
        MetricCallout(value=m.value, label=m.label)
        for m in output.metrics
    ]

    # Get customer name from case study data
    cs = _get_case_study(ctx, case_study_index)
    customer_name = cs.get("customer_name", "Customer") if cs else "Customer"

    return CaseStudyPageInput(
        customer_name=customer_name,
        headline=output.headline,
        sections=sections,
        metrics=metrics,
        quote_text=output.quote_text,
        quote_author=output.quote_author,
        quote_title=output.quote_title,
        cta_text=output.cta_text,
        branding=_build_branding(ctx),
    )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


async def generate_case_study_page(
    claude: ClaudeClient,
    ctx: AssetContext,
    case_study_index: int = 0,
) -> CaseStudyPageInput:
    """Generate a case study page and return the rendering input."""
    generator = CaseStudyPageGenerator()
    output = await generator.generate(claude, ctx, case_study_index=case_study_index)
    return map_output_to_case_study_page_input(
        output, ctx, case_study_index  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

register_generator(CaseStudyPageGenerator())
