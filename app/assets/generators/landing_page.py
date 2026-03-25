"""Landing page content generator.

BJC-170: Four template types (lead magnet download, case study, webinar,
demo request), template selection logic, and output → rendering pipeline mapping.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from app.assets.context import AssetContext
from app.assets.models import (
    BrandingConfig,
    CaseStudyPageInput,
    DemoRequestPageInput,
    FormField,
    LandingPageInput,
    LeadMagnetPageInput,
    MetricCallout,
    Section,
    SocialProofConfig,
    WebinarPageInput,
)
from app.assets.prompts.base import PromptTemplate, register_generator
from app.assets.prompts.schemas import (
    CaseStudyPageOutput,
    DemoRequestPageOutput,
    LandingPageSectionOutput,
    LeadMagnetPageOutput,
    WebinarPageOutput,
)
from app.integrations.claude_ai import ClaudeClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TEMPLATE_TYPES = {
    "lead_magnet_download",
    "case_study",
    "webinar",
    "demo_request",
}

_OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "lead_magnet_download": LeadMagnetPageOutput,
    "case_study": CaseStudyPageOutput,
    "webinar": WebinarPageOutput,
    "demo_request": DemoRequestPageOutput,
}

# ---------------------------------------------------------------------------
# Default form fields per template
# ---------------------------------------------------------------------------

DEFAULT_FORM_FIELDS: dict[str, list[FormField]] = {
    "lead_magnet_download": [
        FormField(name="first_name", label="First Name"),
        FormField(name="email", label="Work Email", type="email"),
        FormField(name="company", label="Company"),
        FormField(name="title", label="Job Title"),
    ],
    "case_study": [],
    "webinar": [
        FormField(name="first_name", label="First Name"),
        FormField(name="last_name", label="Last Name"),
        FormField(name="email", label="Work Email", type="email"),
        FormField(name="company", label="Company"),
        FormField(name="title", label="Job Title"),
    ],
    "demo_request": [
        FormField(name="first_name", label="First Name"),
        FormField(name="last_name", label="Last Name"),
        FormField(name="email", label="Work Email", type="email"),
        FormField(name="company", label="Company"),
        FormField(name="title", label="Job Title"),
        FormField(name="phone", label="Phone", type="tel", required=False),
    ],
}

# ---------------------------------------------------------------------------
# Template-specific prompt instructions
# ---------------------------------------------------------------------------


def _lead_magnet_download_instructions(ctx: AssetContext) -> str:
    return (
        "TEMPLATE: LEAD MAGNET DOWNLOAD PAGE\n\n"
        "Create a high-converting lead magnet download landing page.\n\n"
        "GENERATE:\n"
        "- headline: Benefit-driven headline that communicates the specific value of the "
        "lead magnet. Focus on the transformation or outcome, not the format. "
        "Example: 'The Complete Security Compliance Checklist for SaaS Teams' not "
        "'Download Our Checklist'.\n"
        "- subhead: Curiosity-gap subhead that makes the reader want to learn more. "
        "1-2 sentences expanding on the headline's promise. Address the reader's pain point.\n"
        "- value_props: 3-4 specific, concrete value propositions. Each should communicate "
        "a distinct benefit. Start with action verbs or 'Learn how to...' / 'Discover...'. "
        "Be specific — '23-point checklist covering all HIPAA requirements' not 'Comprehensive guide'.\n"
        "- cta_text: Action-oriented button text. Use first-person: 'Get My Free Checklist' or "
        "'Send Me the Guide'. Never use 'Submit' or 'Download'.\n\n"
        "RULES:\n"
        "- Focus on value to the reader, not features of the content\n"
        "- Use specificity — numbers, timeframes, outcomes\n"
        "- The headline should work standalone as an ad or social post\n"
        "- Keep the subhead under 30 words\n"
    )


def _case_study_instructions(ctx: AssetContext) -> str:
    case_study_context = ""
    if ctx.case_studies:
        cs = ctx.case_studies[0]
        name = cs.get("customer_name", "the customer")
        results = cs.get("results", {})
        problem = cs.get("problem", "")
        solution = cs.get("solution", "")
        quote = cs.get("quote", {})

        parts = [f"\nCASE STUDY DATA:\n- Customer: {name}"]
        if problem:
            parts.append(f"- Challenge: {problem}")
        if solution:
            parts.append(f"- Solution: {solution}")
        if results:
            if isinstance(results, dict):
                metrics_str = ", ".join(f"{k}: {v}" for k, v in results.items())
                parts.append(f"- Results: {metrics_str}")
            else:
                parts.append(f"- Results: {results}")
        if quote and isinstance(quote, dict):
            q_text = quote.get("text", "")
            q_author = quote.get("author", "")
            q_title = quote.get("title", "")
            if q_text:
                parts.append(f'- Quote: "{q_text}" — {q_author}, {q_title}')
        case_study_context = "\n".join(parts)

    return (
        "TEMPLATE: CASE STUDY PAGE\n\n"
        "Create a compelling case study landing page that tells a transformation story.\n\n"
        "GENERATE:\n"
        "- customer_name: The customer's company name\n"
        "- headline: 'How [Customer] achieved [specific, quantified Result]' format. "
        "Lead with the outcome, not the process.\n"
        "- sections: 4 narrative sections following this arc:\n"
        "  1. Situation — who the customer is, their context\n"
        "  2. Challenge — the specific problem they faced, with stakes\n"
        "  3. Solution — how the problem was solved (mention the product naturally)\n"
        "  4. Results — quantified outcomes, specific metrics, timeline\n"
        "  Each section needs: heading, body (2-3 paragraphs), optional bullets for key points, "
        "optional callout for a stat or quote.\n"
        "- metrics: 2-4 metric callouts as {value, label} objects. "
        "Use real numbers from the case study data. Format values for impact: "
        "'3x' not '300%', '47%' not '0.47'.\n"
        "- quote_text, quote_author, quote_title: Customer testimonial if available\n"
        "- cta_text: Outcome-focused CTA: 'Get Similar Results' or 'See How We Can Help'\n\n"
        "RULES:\n"
        "- Tell a story, not a sales pitch — the customer is the hero\n"
        "- Use specific numbers and timelines, not vague claims\n"
        "- The customer's voice (quotes) should feel authentic, not scripted\n"
        "- Every section should flow naturally into the next\n"
        f"{case_study_context}"
    )


def _webinar_instructions(ctx: AssetContext) -> str:
    return (
        "TEMPLATE: WEBINAR REGISTRATION PAGE\n\n"
        "Create a webinar registration landing page that drives signups.\n\n"
        "GENERATE:\n"
        "- event_name: Professional event name that communicates the topic and value. "
        "Example: 'Mastering B2B Lead Gen: Strategies That Actually Convert'\n"
        "- headline: FOMO-driven headline emphasizing what attendees will gain. "
        "Use urgency and specificity: 'Learn the 5 Strategies Top SaaS Teams Use to "
        "Cut CAC by 40%' not 'Join Our Webinar'.\n"
        "- agenda: 5-7 specific learning outcomes or agenda items. Each should be a "
        "concrete takeaway the attendee will walk away with. Start with action verbs: "
        "'Learn', 'Discover', 'Master', 'Understand'. Be specific enough to create "
        "anticipation.\n"
        "- cta_text: Urgency-driven registration CTA: 'Reserve My Spot' or "
        "'Save My Seat'. Never just 'Register'.\n\n"
        "RULES:\n"
        "- Focus on what the attendee will learn, not who is presenting\n"
        "- Each agenda item should stand alone as a reason to attend\n"
        "- Create urgency without being pushy\n"
        "- Agenda items should progress from foundational to advanced\n"
    )


def _demo_request_instructions(ctx: AssetContext) -> str:
    return (
        "TEMPLATE: DEMO REQUEST PAGE\n\n"
        "Create a demo request landing page using problem-agitation-solution structure.\n\n"
        "GENERATE:\n"
        "- headline: Pain-point headline that names the reader's problem directly. "
        "Example: 'Tired of Spending 40 Hours on Month-End Close?' not "
        "'See Our Product in Action'.\n"
        "- subhead: Agitate then resolve — acknowledge the pain, hint at the solution. "
        "1-2 sentences. Example: 'Manual processes are costing you time and accuracy. "
        "See how automation can cut your close time in half.'\n"
        "- benefits: 3 benefit sections, each with:\n"
        "  - heading: Benefit-driven section title (outcome, not feature)\n"
        "  - body: 2-3 sentences explaining how this benefit solves a specific problem. "
        "Use concrete examples and outcomes.\n"
        "  - bullets: 2-3 supporting points (optional)\n"
        "  - callout: Trust signal or proof point (optional)\n"
        "- cta_text: Low-friction CTA: 'See It in Action' or 'Get a Personalized Demo'. "
        "Emphasize it's free and no-commitment.\n\n"
        "RULES:\n"
        "- Lead with problems, not features — the reader should feel understood\n"
        "- Problem-Agitation-Solution structure: name the pain, make it visceral, offer relief\n"
        "- Each benefit section should address a different pain point\n"
        "- Keep the tone empathetic, not salesy\n"
        "- Include trust signals: 'No credit card required', 'Free 30-minute demo'\n"
    )


_TEMPLATE_BUILDERS: dict[str, Any] = {
    "lead_magnet_download": _lead_magnet_download_instructions,
    "case_study": _case_study_instructions,
    "webinar": _webinar_instructions,
    "demo_request": _demo_request_instructions,
}


# ---------------------------------------------------------------------------
# Template selection logic
# ---------------------------------------------------------------------------


def select_landing_page_template(ctx: AssetContext) -> str:
    """Select the best landing page template based on campaign context.

    Priority:
    1. webinar — when objective mentions event/webinar
    2. demo_request — when objective mentions demo/consultation
    3. case_study — when case study data exists in tenant_context
    4. lead_magnet_download — default / when campaign has a lead magnet asset
    """
    objective = (ctx.objective or "").lower()
    angle = (ctx.angle or "").lower()
    combined = f"{objective} {angle}"

    if any(kw in combined for kw in ("webinar", "event", "registration")):
        return "webinar"

    if any(kw in combined for kw in ("demo", "consultation", "request demo", "trial")):
        return "demo_request"

    if ctx.case_studies and any(
        kw in combined for kw in ("case study", "customer story", "success story")
    ):
        return "case_study"

    return "lead_magnet_download"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _build_branding(ctx: AssetContext) -> BrandingConfig:
    """Build BrandingConfig from AssetContext."""
    return BrandingConfig(company_name=ctx.company_name or "")


def _build_social_proof(ctx: AssetContext) -> SocialProofConfig | None:
    """Build SocialProofConfig from AssetContext when data is available.

    Priority: testimonial quote > customer logos > None
    """
    if ctx.testimonials:
        t = ctx.testimonials[0]
        return SocialProofConfig(
            type="quote",
            quote_text=t.get("quote", ""),
            quote_author=t.get("author", ""),
            quote_title=t.get("title", ""),
        )

    if ctx.customer_logos:
        return SocialProofConfig(type="logos", logos=ctx.customer_logos)

    return None


# ---------------------------------------------------------------------------
# Output → rendering pipeline mapping
# ---------------------------------------------------------------------------


def map_lead_magnet_page(
    output: LeadMagnetPageOutput, ctx: AssetContext,
) -> LeadMagnetPageInput:
    """Map LeadMagnetPageOutput → LeadMagnetPageInput."""
    return LeadMagnetPageInput(
        headline=output.headline,
        subhead=output.subhead,
        value_props=output.value_props,
        cta_text=output.cta_text,
        form_fields=DEFAULT_FORM_FIELDS["lead_magnet_download"],
        branding=_build_branding(ctx),
        social_proof=_build_social_proof(ctx),
    )


def map_case_study_page(
    output: CaseStudyPageOutput, ctx: AssetContext,
) -> CaseStudyPageInput:
    """Map CaseStudyPageOutput → CaseStudyPageInput."""
    sections = [
        Section(
            heading=s.heading,
            body=s.body,
            bullets=s.bullets,
            callout=s.callout,
        )
        for s in output.sections
    ]

    metrics = [
        MetricCallout(value=m.get("value", ""), label=m.get("label", ""))
        for m in output.metrics
    ]

    return CaseStudyPageInput(
        customer_name=output.customer_name,
        headline=output.headline,
        sections=sections,
        metrics=metrics,
        quote_text=output.quote_text,
        quote_author=output.quote_author,
        quote_title=output.quote_title,
        cta_text=output.cta_text,
        form_fields=DEFAULT_FORM_FIELDS["case_study"],
        branding=_build_branding(ctx),
    )


def map_webinar_page(
    output: WebinarPageOutput, ctx: AssetContext,
    event_date: str = "TBD",
    speakers: list[dict] | None = None,
) -> WebinarPageInput:
    """Map WebinarPageOutput → WebinarPageInput."""
    return WebinarPageInput(
        event_name=output.event_name,
        event_date=event_date,
        headline=output.headline,
        speakers=speakers or [],
        agenda=output.agenda,
        cta_text=output.cta_text,
        form_fields=DEFAULT_FORM_FIELDS["webinar"],
        branding=_build_branding(ctx),
    )


def map_demo_request_page(
    output: DemoRequestPageOutput, ctx: AssetContext,
) -> DemoRequestPageInput:
    """Map DemoRequestPageOutput → DemoRequestPageInput."""
    benefits = [
        Section(
            heading=s.heading,
            body=s.body,
            bullets=s.bullets,
            callout=s.callout,
        )
        for s in output.benefits
    ]

    return DemoRequestPageInput(
        headline=output.headline,
        subhead=output.subhead,
        benefits=benefits,
        cta_text=output.cta_text,
        trust_signals=_build_social_proof(ctx),
        form_fields=DEFAULT_FORM_FIELDS["demo_request"],
        branding=_build_branding(ctx),
    )


_MAPPERS = {
    "lead_magnet_download": map_lead_magnet_page,
    "case_study": map_case_study_page,
    "webinar": map_webinar_page,
    "demo_request": map_demo_request_page,
}


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class LandingPageGenerator(PromptTemplate):
    """Generator for landing page content across 4 template types."""

    asset_type = "landing_page"
    model = ClaudeClient.MODEL_QUALITY
    output_schema = LeadMagnetPageOutput  # default; overridden per template in generate()
    temperature = 0.5

    def build_asset_specific_instructions(self, ctx: AssetContext, **kwargs: Any) -> str:
        """Build template-specific prompt instructions.

        Accepts ``template_type`` kwarg to select one of the 4 landing page templates.
        """
        template_type = kwargs.get("template_type", "lead_magnet_download")
        if template_type not in _TEMPLATE_BUILDERS:
            raise ValueError(
                f"Unknown landing page template '{template_type}'. "
                f"Valid: {sorted(VALID_TEMPLATE_TYPES)}"
            )

        builder = _TEMPLATE_BUILDERS[template_type]
        return builder(ctx)

    async def generate(
        self,
        claude: ClaudeClient,
        ctx: AssetContext,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate landing page content with the correct output schema per template."""
        template_type = kwargs.get("template_type", "lead_magnet_download")
        if template_type not in _OUTPUT_SCHEMAS:
            raise ValueError(
                f"Unknown landing page template '{template_type}'. "
                f"Valid: {sorted(VALID_TEMPLATE_TYPES)}"
            )

        # Override output schema per template type
        original_schema = self.output_schema
        self.output_schema = _OUTPUT_SCHEMAS[template_type]
        try:
            return await super().generate(claude, ctx, **kwargs)
        finally:
            self.output_schema = original_schema


# ---------------------------------------------------------------------------
# Top-level convenience function
# ---------------------------------------------------------------------------


async def generate_landing_page(
    claude: ClaudeClient,
    ctx: AssetContext,
    template_type: str,
    event_date: str = "TBD",
    speakers: list[dict] | None = None,
) -> LandingPageInput:
    """Generate content via Claude → map to rendering input → return."""
    generator = LandingPageGenerator()
    output = await generator.generate(claude, ctx, template_type=template_type)

    if template_type == "lead_magnet_download":
        return map_lead_magnet_page(output, ctx)  # type: ignore[arg-type]
    elif template_type == "case_study":
        return map_case_study_page(output, ctx)  # type: ignore[arg-type]
    elif template_type == "webinar":
        return map_webinar_page(output, ctx, event_date=event_date, speakers=speakers)  # type: ignore[arg-type]
    elif template_type == "demo_request":
        return map_demo_request_page(output, ctx)  # type: ignore[arg-type]
    else:
        raise ValueError(
            f"Unknown landing page template '{template_type}'. "
            f"Valid: {sorted(VALID_TEMPLATE_TYPES)}"
        )


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

register_generator(LandingPageGenerator())
