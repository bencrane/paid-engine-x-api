"""Email nurture sequence content generator.

BJC-172: 5-email progressive nurture sequence with personalization tokens,
spam-safe subject lines, and trigger-based prompt customization.
"""

from __future__ import annotations

import logging
from typing import Any

from app.assets.context import AssetContext
from app.assets.prompts.base import PromptTemplate, register_generator
from app.assets.prompts.schemas import EmailSequenceOutput
from app.integrations.claude_ai import ClaudeClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Trigger types and sequence configs
# ---------------------------------------------------------------------------

VALID_TRIGGERS = {
    "lead_magnet_download",
    "webinar_registration",
    "demo_request",
}

_TRIGGER_CONTEXT: dict[str, str] = {
    "lead_magnet_download": (
        "TRIGGER: Lead Magnet Download\n"
        "The prospect just downloaded a lead magnet (PDF, checklist, guide, etc.). "
        "They are top-of-funnel and have shown interest in the topic but have NOT "
        "expressed buying intent yet.\n"
        "- Email 1 should deliver the asset and provide an immediate insight\n"
        "- The sequence should build from educational value to soft pitch\n"
    ),
    "webinar_registration": (
        "TRIGGER: Webinar Registration\n"
        "The prospect registered for a webinar. They have shown interest in the topic "
        "and are willing to invest time. This is mid-funnel behavior.\n"
        "- Email 1 should confirm registration and tease key insights\n"
        "- Include a pre-webinar warm-up email\n"
        "- Post-webinar follow-up should reference specific content from the session\n"
    ),
    "demo_request": (
        "TRIGGER: Demo Request\n"
        "The prospect requested a demo. This is high-intent, bottom-of-funnel behavior. "
        "They are actively evaluating solutions.\n"
        "- Email 1 should confirm the request and set expectations\n"
        "- Sequence should reinforce value, address objections, and provide social proof\n"
        "- Accelerated cadence — they are ready to buy\n"
    ),
}


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class EmailCopyGenerator(PromptTemplate):
    """Generator for email nurture sequences."""

    asset_type = "email_copy"
    model = ClaudeClient.MODEL_FAST
    output_schema = EmailSequenceOutput
    temperature = 0.5

    def build_asset_specific_instructions(self, ctx: AssetContext, **kwargs: Any) -> str:
        """Build email sequence prompt instructions.

        Accepts ``trigger`` kwarg to customize the sequence context.
        """
        trigger = kwargs.get("trigger", "lead_magnet_download")

        parts: list[str] = []

        # Trigger context
        trigger_block = _TRIGGER_CONTEXT.get(trigger, _TRIGGER_CONTEXT["lead_magnet_download"])
        parts.append(trigger_block)

        # Core sequence instructions
        parts.append(
            "SEQUENCE STRUCTURE:\n"
            "Generate a 5-email nurture sequence with progressive disclosure.\n"
            "Each email builds trust incrementally — helpful → credible → earned ask.\n\n"
            "EMAIL PROGRESSION:\n"
            "1. Day 0 — Value Delivery (purpose: value_delivery)\n"
            "   Thank the prospect, deliver the asset or confirm the action, and "
            "tease one key insight to encourage them to open the next email.\n\n"
            "2. Day 2 — Education (purpose: education)\n"
            "   Expand on the topic with a related insight, framework, or tip. "
            "Position the company as a knowledgeable resource. No selling.\n\n"
            "3. Day 5 — Social Proof (purpose: social_proof)\n"
            "   Share a brief case study snippet, customer quote, or specific result. "
            "Let the outcomes speak — 'BigCo reduced X by 40%' not 'Our product is great'.\n\n"
            "4. Day 8 — Soft Pitch (purpose: soft_pitch)\n"
            "   Bridge from value to product: 'Companies like yours use [product] to [outcome]'. "
            "Introduce the product naturally as a solution to the pain points discussed.\n\n"
            "5. Day 12 — Direct CTA (purpose: direct_cta)\n"
            "   Clear, direct ask with urgency. Demo, consultation, or trial. "
            "Summarize the value delivered and make the next step easy.\n"
        )

        # Subject line and formatting rules
        parts.append(
            "SUBJECT LINE RULES:\n"
            "- Max 60 characters\n"
            "- Specific and curiosity-driven — not generic ('Quick question about X')\n"
            "- Avoid spam triggers: no ALL CAPS, no 'free', no 'act now', "
            "no excessive punctuation (!!!, ???), no misleading Re:/Fwd:\n"
            "- Use the prospect's context when possible\n"
            "- Test patterns: question, number, how-to, curiosity gap\n"
        )

        parts.append(
            "PREVIEW TEXT RULES:\n"
            "- Max 90 characters\n"
            "- Complements (not repeats) the subject line\n"
            "- Creates additional reason to open\n"
        )

        parts.append(
            "BODY RULES:\n"
            "- Conversational B2B tone — write like a helpful colleague, not a marketer\n"
            "- Short paragraphs (2-3 sentences max)\n"
            "- Single CTA per email — one clear next step\n"
            "- Include personalization tokens: {{first_name}}, {{company}}\n"
            "- Use 'you' and 'your' language — reader-centric\n"
            "- Body should be valid HTML with proper paragraph tags\n"
            "- Progressive tone: Email 1-2 helpful → Email 3 credible → Email 4-5 earned ask\n"
        )

        parts.append(
            "FORMATTING:\n"
            "- send_delay_days: 0, 2, 5, 8, 12 (standard nurture cadence)\n"
            "- purpose: must match the progression — value_delivery, education, "
            "social_proof, soft_pitch, direct_cta\n"
            "- sequence_name: Descriptive name for the sequence\n"
            f"- trigger: '{trigger}'\n"
        )

        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


async def generate_email_sequence(
    claude: ClaudeClient,
    ctx: AssetContext,
    trigger: str = "lead_magnet_download",
) -> EmailSequenceOutput:
    """Generate a nurture email sequence for the given trigger."""
    if trigger not in VALID_TRIGGERS:
        raise ValueError(
            f"Unknown trigger '{trigger}'. Valid: {sorted(VALID_TRIGGERS)}"
        )
    generator = EmailCopyGenerator()
    result = await generator.generate(claude, ctx, trigger=trigger)
    return result  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

register_generator(EmailCopyGenerator())
