"""Video script content generator.

BJC-175: Duration-specific video scripts (30s / 60s) with platform guidance,
aspect ratio selection, and word-count-aware segment templates.
"""

from __future__ import annotations

import logging
from typing import Any

from app.assets.context import AssetContext
from app.assets.prompts.base import PromptTemplate, register_generator
from app.assets.prompts.schemas import VideoScriptOutput
from app.integrations.claude_ai import ClaudeClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Duration configs
# ---------------------------------------------------------------------------

VALID_DURATIONS = {"30s", "60s"}

_DURATION_STRUCTURES: dict[str, str] = {
    "30s": (
        "DURATION: 30 seconds (~75 words total spoken text)\n\n"
        "SEGMENT STRUCTURE:\n"
        "1. Hook (0:00–0:03) — 1 sentence, max 10 words. "
        "Grab attention immediately with a bold claim, question, or stat.\n"
        "2. Problem (0:03–0:10) — 2 sentences. Name the pain the viewer feels. "
        "Be specific to the persona.\n"
        "3. Solution (0:10–0:20) — 2-3 sentences. Show how the product solves the "
        "problem. Focus on ONE key benefit, not a feature list.\n"
        "4. CTA (0:20–0:30) — 1-2 sentences. Clear next step with urgency. "
        "Tell them exactly what to do.\n\n"
        "The hook is the first ScriptSegment. "
        "Problem and Solution go in the body list. "
        "CTA is the final ScriptSegment.\n"
    ),
    "60s": (
        "DURATION: 60 seconds (~150 words total spoken text)\n\n"
        "SEGMENT STRUCTURE:\n"
        "1. Hook (0:00–0:03) — 1 sentence, max 10 words. "
        "Grab attention immediately.\n"
        "2. Problem (0:03–0:15) — 3-4 sentences. Deep dive into the pain. "
        "Make the viewer nod along.\n"
        "3. Solution (0:15–0:35) — 4-5 sentences. Show the product solving the "
        "problem. Include a concrete example or walkthrough moment.\n"
        "4. Proof (0:35–0:50) — 2-3 sentences. Social proof, stat, or "
        "customer result. 'BigCo reduced X by 40%' style.\n"
        "5. CTA (0:50–1:00) — 1-2 sentences. Clear next step with urgency.\n\n"
        "The hook is the first ScriptSegment. "
        "Problem, Solution, and Proof go in the body list. "
        "CTA is the final ScriptSegment.\n"
    ),
}

# ---------------------------------------------------------------------------
# Platform guidance
# ---------------------------------------------------------------------------

VALID_PLATFORMS = {"linkedin", "meta", "youtube"}

_PLATFORM_GUIDANCE: dict[str, str] = {
    "linkedin": (
        "PLATFORM: LinkedIn Video\n"
        "- Aspect ratio: 4:5 (portrait, optimal for LinkedIn feed)\n"
        "- Tone: Professional, authoritative, conversational. "
        "Speak like a trusted advisor, not a salesperson.\n"
        "- Caption-heavy: assume most viewers watch without sound. "
        "Every segment MUST have caption_text that conveys the full message.\n"
        "- Text overlays: use bold key stats or pull-quotes as on-screen text.\n"
        "- Opening: hook must work as a silent thumbnail — "
        "visual_direction should describe an attention-grabbing first frame.\n"
    ),
    "meta": (
        "PLATFORM: Meta (Facebook / Instagram Reels)\n"
        "- Aspect ratio: 4:5 for feed, 9:16 for Reels/Stories\n"
        "- Tone: Punchy, fast-paced, scroll-stopping. "
        "You have 1 second to earn the next 3.\n"
        "- Hook MUST be visually disruptive — movement, bold text, or "
        "unexpected imagery in the first frame.\n"
        "- Short sentences, fast cuts. No segment longer than 10 seconds.\n"
        "- Captions are critical — most views are sound-off.\n"
        "- Emojis OK in text overlays (sparingly).\n"
    ),
    "youtube": (
        "PLATFORM: YouTube\n"
        "- Aspect ratio: 16:9 (landscape, standard YouTube)\n"
        "- Tone: Educational, value-first. "
        "Viewers chose to watch — reward their attention.\n"
        "- Hook should promise a specific takeaway: "
        "'In the next 30/60 seconds, you'll learn...'\n"
        "- More breathing room — slightly longer sentences are OK.\n"
        "- Visual direction should describe b-roll, screen recordings, "
        "or talking-head setups.\n"
        "- End screen CTA: mention subscribe + link in description.\n"
    ),
}

_PLATFORM_ASPECT_RATIOS: dict[str, str] = {
    "linkedin": "4:5",
    "meta": "4:5",
    "youtube": "16:9",
}


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class VideoScriptGenerator(PromptTemplate):
    """Generator for video scripts."""

    asset_type = "video_script"
    model = ClaudeClient.MODEL_FAST
    output_schema = VideoScriptOutput
    temperature = 0.5

    def build_asset_specific_instructions(self, ctx: AssetContext, **kwargs: Any) -> str:
        """Build video script prompt instructions.

        Accepts ``duration`` (30s | 60s) and ``platform`` (linkedin | meta | youtube).
        """
        duration: str = kwargs.get("duration", "30s")
        platform: str = kwargs.get("platform", "linkedin")

        if duration not in VALID_DURATIONS:
            raise ValueError(
                f"Unknown duration '{duration}'. Valid: {sorted(VALID_DURATIONS)}"
            )
        if platform not in VALID_PLATFORMS:
            raise ValueError(
                f"Unknown video platform '{platform}'. Valid: {sorted(VALID_PLATFORMS)}"
            )

        parts: list[str] = []

        # Duration structure
        parts.append(_DURATION_STRUCTURES[duration])

        # Platform guidance
        parts.append(_PLATFORM_GUIDANCE[platform])

        # Aspect ratio instruction
        aspect_ratio = _PLATFORM_ASPECT_RATIOS[platform]
        parts.append(f"Set aspect_ratio to '{aspect_ratio}'.")
        parts.append(f"Set target_platform to '{platform}'.")
        parts.append(f"Set duration to '{duration}'.")

        # Segment rules
        parts.append(
            "SEGMENT RULES:\n"
            "- timestamp_start / timestamp_end: use 'M:SS' format (e.g., '0:00', '0:03')\n"
            "- spoken_text: the exact words the speaker says\n"
            "- visual_direction: describe the shot — camera angle, subject, motion, "
            "b-roll, screen recording, etc. Be specific.\n"
            "- text_overlay: on-screen text (null if none). Bold stats, key phrases, "
            "or CTA text.\n"
            "- caption_text: subtitle text for sound-off viewing. "
            "Must convey the full message even without audio.\n"
        )

        # Word count
        word_target = 75 if duration == "30s" else 150
        parts.append(
            f"WORD COUNT:\n"
            f"- Target ~{word_target} total words across all spoken_text fields.\n"
            f"- Set total_word_count to the actual count.\n"
            f"- Pace: ~2.5 words per second for natural delivery.\n"
        )

        # Music direction
        parts.append(
            "MUSIC DIRECTION:\n"
            "- Provide a brief music direction (genre, tempo, mood).\n"
            "- Example: 'Upbeat electronic, 120 BPM, builds to crescendo at CTA'\n"
            "- Music should complement the tone, not compete with speech.\n"
        )

        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


async def generate_video_script(
    claude: ClaudeClient,
    ctx: AssetContext,
    duration: str = "30s",
    platform: str = "linkedin",
) -> VideoScriptOutput:
    """Generate a video script for the given duration and platform."""
    if duration not in VALID_DURATIONS:
        raise ValueError(
            f"Unknown duration '{duration}'. Valid: {sorted(VALID_DURATIONS)}"
        )
    if platform not in VALID_PLATFORMS:
        raise ValueError(
            f"Unknown video platform '{platform}'. Valid: {sorted(VALID_PLATFORMS)}"
        )
    generator = VideoScriptGenerator()
    result = await generator.generate(claude, ctx, duration=duration, platform=platform)
    return result  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

register_generator(VideoScriptGenerator())
