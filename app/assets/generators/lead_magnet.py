"""Lead Magnet PDF content generator.

BJC-169: Five format-specific prompt templates, two-pass generation for long
formats, industry vertical handling, and output → rendering pipeline mapping.
"""

from __future__ import annotations

import logging
from typing import Any

from app.assets.context import AssetContext
from app.assets.models import BrandingConfig, LeadMagnetPDFInput, PDFSection
from app.assets.prompts.base import PromptTemplate, register_generator
from app.assets.prompts.schemas import LeadMagnetOutput, LeadMagnetSectionOutput
from app.integrations.claude_ai import ClaudeClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Format configs
# ---------------------------------------------------------------------------

LEAD_MAGNET_FORMATS: dict[str, dict[str, Any]] = {
    "checklist": {
        "temperature": 0.3,
        "word_range": "2,000–4,000",
        "two_pass": False,
    },
    "ultimate_guide": {
        "temperature": 0.7,
        "word_range": "5,500–8,500",
        "two_pass": True,
    },
    "benchmark_report": {
        "temperature": 0.5,
        "word_range": "4,000–8,000",
        "two_pass": False,
    },
    "template_toolkit": {
        "temperature": 0.4,
        "word_range": "3,000–6,000",
        "two_pass": False,
    },
    "state_of_industry": {
        "temperature": 0.6,
        "word_range": "6,000–10,000",
        "two_pass": True,
    },
}

VALID_FORMATS = set(LEAD_MAGNET_FORMATS.keys())

# ---------------------------------------------------------------------------
# Industry vertical guidance
# ---------------------------------------------------------------------------

INDUSTRY_GUIDANCE: dict[str, str] = {
    "SaaS": (
        "INDUSTRY GUIDANCE (Tech/SaaS):\n"
        "- Tone: Casual-professional, technical but accessible\n"
        "- Include tool recommendations, integration references, and metric-driven examples\n"
        "- Use concrete SaaS metrics (MRR, churn, NRR, CAC payback) where relevant\n"
        "- CTA: Free trial, demo request, or 'Talk to an engineer'"
    ),
    "Healthcare": (
        "INDUSTRY GUIDANCE (Healthcare):\n"
        "- Tone: Formal, evidence-based, patient-safety awareness throughout\n"
        "- Reference relevant regulations (HIPAA, FDA, HITECH) where applicable\n"
        "- Use clinical language and cite peer-reviewed sources when possible\n"
        "- Include compliance and regulatory callouts\n"
        "- CTA: Consultation, white paper download, or ROI calculator"
    ),
    "Financial Services": (
        "INDUSTRY GUIDANCE (Financial Services):\n"
        "- Tone: Conservative, precise, data-heavy\n"
        "- Reference regulatory bodies (FinCEN, OCC, SEC, CFPB) as appropriate\n"
        "- Emphasize risk management, compliance, and quantifiable outcomes\n"
        "- Include relevant disclaimer language\n"
        "- CTA: Consultation, assessment, or custom report"
    ),
    "Manufacturing": (
        "INDUSTRY GUIDANCE (Manufacturing):\n"
        "- Tone: Practical, ROI-focused, process-oriented\n"
        "- Use quality/safety language (Six Sigma, ISO, lean manufacturing)\n"
        "- Include process flow references, measurement criteria, and ROI calculations\n"
        "- CTA: Plant tour, ROI assessment, or pilot program"
    ),
}


# ---------------------------------------------------------------------------
# Format-specific prompt instructions
# ---------------------------------------------------------------------------


def _checklist_instructions(ctx: AssetContext) -> str:
    return (
        "FORMAT: CHECKLIST\n\n"
        "Create a B2B checklist lead magnet with the following structure:\n\n"
        "STRUCTURE:\n"
        "- 4–6 category sections, each with a descriptive heading\n"
        "- 15–25 total checklist items across all sections\n"
        "- Total word count: 2,000–4,000 words\n\n"
        "SECTION FORMAT:\n"
        "- heading: Category group name (e.g., 'Pre-Launch Security', 'Ongoing Monitoring')\n"
        "- body: Brief category introduction (1–2 sentences explaining why this category matters)\n"
        "- bullets: The checklist items themselves — each MUST start with an imperative action verb "
        "(Configure, Review, Verify, Document, Enable, Audit, etc.). "
        "Each item: action verb + task (5–15 words) + brief explanation (10–25 words)\n"
        "- callout_box: Pro tip, 'why this matters' note, or key statistic (1–2 sentences). "
        "Use for 2–3 sections, leave null for others.\n\n"
        "RULES:\n"
        "- Every checklist item must be specific enough to act on immediately — "
        "no vague advice like 'Implement best practices'\n"
        "- Include concrete tools, metrics, or thresholds where relevant\n"
        "- No product pitching in the checklist body\n"
        "- Maintain consistent item length and formatting\n"
        "- Group items logically (chronological, priority, or functional area)\n"
    )


def _ultimate_guide_instructions(ctx: AssetContext) -> str:
    return (
        "FORMAT: ULTIMATE GUIDE\n\n"
        "Create a comprehensive B2B ultimate guide with the following structure:\n\n"
        "STRUCTURE:\n"
        "- 5 chapters, each 800–1,800 words\n"
        "- Total word count: 5,500–8,500 words\n"
        "- Chapter progression: Foundations → Framework → Tactical How-To → "
        "Advanced Strategies → Future Trends\n\n"
        "SECTION FORMAT:\n"
        "- heading: Chapter title (descriptive, value-communicating)\n"
        "- body: Chapter prose — educational, specific, with concrete examples and data points. "
        "Every paragraph must contain either a specific example, a data point, an actionable step, "
        "or an expert insight. No filler.\n"
        "- bullets: 3–5 key takeaways per chapter — the most important lessons condensed\n"
        "- callout_box: Stat highlight, expert quote, or pro tip (1 per chapter). "
        "Use for notable data or contrarian insights.\n\n"
        "RULES:\n"
        "- Write from a position of deep expertise, not surface-level overview\n"
        "- Avoid corporate buzzwords: no 'leverage', 'synergy', 'cutting-edge', "
        "'in today's fast-paced world', 'game-changer'\n"
        "- Include a named framework or methodology in Chapter 2 (can be branded)\n"
        "- Chapter 3 must be actionable — step-by-step with specific tools and examples\n"
        "- Only use statistics provided in the context. Do not invent statistics.\n"
        "- Each chapter should build on the previous — maintain narrative coherence\n"
    )


def _benchmark_report_instructions(ctx: AssetContext) -> str:
    return (
        "FORMAT: BENCHMARK REPORT\n\n"
        "Create a data-driven benchmark report with the following structure:\n\n"
        "STRUCTURE:\n"
        "- Executive summary section (first section): 3–5 key findings as bold declarative "
        "statements with 1–2 sentences of context each\n"
        "- 3–5 metric category sections: each analyzing a benchmark area with data-backed narrative\n"
        "- Recommendations section (final section): actionable next steps based on findings\n"
        "- Total word count: 4,000–8,000 words\n\n"
        "SECTION FORMAT:\n"
        "- heading: Metric category name or 'Executive Summary' / 'Recommendations'\n"
        "- body: Analytical narrative — authoritative, data-forward, insight-driven. "
        "Format findings as: '[Metric] is [X], [up/down Y%] from [period] — meaning [implication]'\n"
        "- bullets: Key findings or recommendations as bullet points\n"
        "- callout_box: Large stat callout with context (e.g., 'Only 23% of companies achieve X — "
        "down from 31% last year'). One per section.\n\n"
        "RULES:\n"
        "- Lead each section with the most surprising or counterintuitive finding\n"
        "- Every finding must include comparative context (YoY, industry avg, peer group)\n"
        "- Executive summary should give 80% of the value — busy executives stop there\n"
        "- Only use data and statistics provided in the context. Do not fabricate numbers.\n"
        "- Tone: Authoritative, concise, insight-forward. No fluff.\n"
    )


def _template_toolkit_instructions(ctx: AssetContext) -> str:
    return (
        "FORMAT: TEMPLATE / TOOLKIT\n\n"
        "Create a practical template toolkit with the following structure:\n\n"
        "STRUCTURE:\n"
        "- Introduction section: Explain the toolkit's purpose, who it's for, and how to use it\n"
        "- 4–6 template sections: each a standalone, usable template with instructions\n"
        "- Total word count: 3,000–6,000 words\n\n"
        "SECTION FORMAT:\n"
        "- heading: Template name (descriptive — e.g., 'Campaign Brief Template', "
        "'ROI Calculator Framework')\n"
        "- body: Instructions and context — explain when to use this template, "
        "what it accomplishes, and how to customize it. Include fill-in-the-blank "
        "placeholders like [Your Company Name] or [Target Metric].\n"
        "- bullets: Step-by-step numbered instructions for completing the template "
        "(5–10 steps per template)\n"
        "- callout_box: Pro tip or 'common mistakes to avoid' (1–2 sentences). "
        "Use for 2–3 sections.\n\n"
        "RULES:\n"
        "- Every template must be immediately usable — not just advice, but an actual framework\n"
        "- Include placeholder text the reader can fill in\n"
        "- Step-by-step instructions should be specific and sequential\n"
        "- Tone: Instructional, practical, encouraging\n"
        "- Show before/after examples where helpful\n"
    )


def _state_of_industry_instructions(ctx: AssetContext) -> str:
    return (
        "FORMAT: STATE OF THE INDUSTRY REPORT\n\n"
        "Create an authoritative industry report with the following structure:\n\n"
        "STRUCTURE:\n"
        "- Executive summary section (first section): 3–5 headline findings that tell the full story\n"
        "- 4–6 finding sections: each analyzing a major trend or insight\n"
        "- Implications section (final section): what these findings mean for the reader's strategy\n"
        "- Total word count: 6,000–10,000 words\n\n"
        "SECTION FORMAT:\n"
        "- heading: Finding or trend headline (declarative — e.g., 'AI Adoption Accelerates but "
        "ROI Remains Elusive')\n"
        "- body: Analytical narrative — authoritative, insight-driven, connecting data to "
        "strategic implications. Build from observation → evidence → implication.\n"
        "- bullets: Key implications, recommendations, or supporting data points\n"
        "- callout_box: Big number callout or expert quote. One per section.\n\n"
        "RULES:\n"
        "- Position as forward-looking thought leadership, not just data summary\n"
        "- Every finding must answer 'so what?' — connect data to reader impact\n"
        "- Include 12–24 month predictions grounded in current evidence\n"
        "- Only use data and statistics provided in the context. Do not invent numbers.\n"
        "- Tone: Authoritative, insight-driven, visionary but grounded\n"
    )


_FORMAT_BUILDERS: dict[str, Any] = {
    "checklist": _checklist_instructions,
    "ultimate_guide": _ultimate_guide_instructions,
    "benchmark_report": _benchmark_report_instructions,
    "template_toolkit": _template_toolkit_instructions,
    "state_of_industry": _state_of_industry_instructions,
}


# ---------------------------------------------------------------------------
# Format selection helper
# ---------------------------------------------------------------------------


def select_lead_magnet_format(angle: str, objective: str, industry: str) -> str:
    """Suggest the best lead magnet format based on campaign context.

    Heuristic scoring based on keyword signals in angle/objective/industry.
    """
    angle_lower = (angle or "").lower()
    objective_lower = (objective or "").lower()
    industry_lower = (industry or "").lower()
    combined = f"{angle_lower} {objective_lower} {industry_lower}"

    scores: dict[str, int] = {fmt: 0 for fmt in VALID_FORMATS}

    # Checklist signals
    for kw in ("compliance", "audit", "checklist", "launch", "onboarding", "security", "setup"):
        if kw in combined:
            scores["checklist"] += 2

    # Ultimate guide signals
    for kw in ("guide", "education", "how to", "learn", "comprehensive", "strategy"):
        if kw in combined:
            scores["ultimate_guide"] += 2

    # Benchmark report signals
    for kw in ("benchmark", "data", "metrics", "performance", "comparison", "analytics"):
        if kw in combined:
            scores["benchmark_report"] += 2

    # Template toolkit signals
    for kw in ("template", "toolkit", "framework", "worksheet", "planner", "calculator"):
        if kw in combined:
            scores["template_toolkit"] += 2

    # State of industry signals
    for kw in ("state of", "trends", "industry", "forecast", "outlook", "market", "survey"):
        if kw in combined:
            scores["state_of_industry"] += 2

    # Objective-based boosts
    if "thought_leadership" in objective_lower or "brand" in objective_lower:
        scores["state_of_industry"] += 1
        scores["ultimate_guide"] += 1
    if "lead_gen" in objective_lower or "lead_generation" in objective_lower:
        scores["checklist"] += 1
        scores["template_toolkit"] += 1

    # Return highest-scoring format, defaulting to checklist on tie
    best = max(scores, key=lambda k: (scores[k], k == "checklist"))
    return best


# ---------------------------------------------------------------------------
# Output → rendering pipeline mapping
# ---------------------------------------------------------------------------


def map_output_to_pdf_input(
    output: LeadMagnetOutput,
    ctx: AssetContext,
) -> LeadMagnetPDFInput:
    """Map Claude's LeadMagnetOutput → LeadMagnetPDFInput for the PDF renderer."""
    sections = [
        PDFSection(
            heading=s.heading,
            body=s.body,
            bullets=s.bullets if s.bullets else None,
            callout_box=s.callout_box,
        )
        for s in output.sections
    ]

    branding = BrandingConfig(company_name=ctx.company_name or "")

    return LeadMagnetPDFInput(
        title=output.title,
        subtitle=output.subtitle,
        sections=sections,
        branding=branding,
    )


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class LeadMagnetGenerator(PromptTemplate):
    """Generator for lead magnet PDF content across 5 formats."""

    asset_type = "lead_magnet"
    model = ClaudeClient.MODEL_QUALITY
    output_schema = LeadMagnetOutput
    temperature = 0.5  # Default; overridden per format in generate()

    def build_asset_specific_instructions(self, ctx: AssetContext, **kwargs: Any) -> str:
        """Build format-specific prompt instructions.

        Accepts ``format`` kwarg to select one of the 5 lead magnet formats.
        """
        fmt = kwargs.get("format", "checklist")
        if fmt not in _FORMAT_BUILDERS:
            raise ValueError(
                f"Unknown lead magnet format '{fmt}'. Valid: {sorted(VALID_FORMATS)}"
            )

        parts: list[str] = []

        # Format-specific instructions
        builder = _FORMAT_BUILDERS[fmt]
        parts.append(builder(ctx))

        # Industry vertical guidance
        industry = ctx.industry or ""
        if industry in INDUSTRY_GUIDANCE:
            parts.append(INDUSTRY_GUIDANCE[industry])
        elif industry:
            parts.append(f"INDUSTRY CONTEXT: {industry} — tailor examples and language accordingly.")

        return "\n\n".join(parts)

    async def generate(
        self,
        claude: ClaudeClient,
        ctx: AssetContext,
        **kwargs: Any,
    ) -> LeadMagnetOutput:
        """Generate lead magnet content, using two-pass for long formats."""
        fmt = kwargs.get("format", "checklist")
        if fmt not in LEAD_MAGNET_FORMATS:
            raise ValueError(
                f"Unknown lead magnet format '{fmt}'. Valid: {sorted(VALID_FORMATS)}"
            )

        # Override temperature per format
        fmt_config = LEAD_MAGNET_FORMATS[fmt]
        original_temp = self.temperature
        self.temperature = fmt_config["temperature"]

        try:
            if fmt_config["two_pass"]:
                return await self._two_pass_generate(claude, ctx, fmt=fmt)
            else:
                return await super().generate(claude, ctx, **kwargs)
        finally:
            self.temperature = original_temp

    async def _two_pass_generate(
        self,
        claude: ClaudeClient,
        ctx: AssetContext,
        fmt: str,
    ) -> LeadMagnetOutput:
        """Two-pass generation for long formats (ultimate_guide, state_of_industry).

        Pass 1: Generate outline (section titles + summaries).
        Pass 2: Expand each section using outline as context.
        """
        system_prompt = self.build_system_prompt(ctx)

        # --- Pass 1: Generate outline ---
        outline_prompt = (
            self.build_user_prompt(ctx, format=fmt)
            + "\n\n"
            "IMPORTANT: For this first pass, generate ONLY an outline.\n"
            "Return a JSON object matching the output schema, but with abbreviated content:\n"
            "- title: The full title\n"
            "- subtitle: The full subtitle\n"
            "- sections: For each section, include:\n"
            "  - heading: The section/chapter title\n"
            "  - body: A 2–3 sentence summary of what this section will cover\n"
            "  - bullets: 3–5 key points to be expanded\n"
            "  - callout_box: null\n"
        )

        outline = await claude.generate_structured(
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=outline_prompt,
            output_schema=self.output_schema,
            temperature=max(self.temperature - 0.1, 0.0),
            asset_type=self.asset_type,
        )

        # --- Pass 2: Expand with outline context ---
        outline_summary = "\n".join(
            f"- {s.heading}: {s.body}" for s in outline.sections
        )

        expand_prompt = (
            self.build_user_prompt(ctx, format=fmt)
            + "\n\n"
            f"OUTLINE (expand each section fully):\n{outline_summary}\n\n"
            "Now generate the COMPLETE content. For each section listed in the outline, "
            "write the full prose, detailed bullets/takeaways, and callout boxes. "
            "Maintain the section order and headings from the outline. "
            "Do not abbreviate — write the full word count for each section."
        )

        result = await claude.generate_structured(
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=expand_prompt,
            output_schema=self.output_schema,
            temperature=self.temperature,
            asset_type=self.asset_type,
        )

        return result


# ---------------------------------------------------------------------------
# Top-level convenience function
# ---------------------------------------------------------------------------


async def generate_lead_magnet(
    claude: ClaudeClient,
    ctx: AssetContext,
    format: str,
) -> LeadMagnetPDFInput:
    """Generate content via Claude → map to rendering input → return."""
    generator = LeadMagnetGenerator()
    output = await generator.generate(claude, ctx, format=format)
    return map_output_to_pdf_input(output, ctx)


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

register_generator(LeadMagnetGenerator())
