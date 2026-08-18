"""Prompt formatting and schema payload for LLM-backed ReelSignal extraction."""

from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import DepthLevel
from scrollsense.domain.reels import InterestEvidence, Reel


class StructuredExtractionPayload(BaseModel):
    """Strict schema expected from LLM structured output generation."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(..., min_length=1, description="Core concise topic, e.g. java_meme, swe_lifestyle")
    format: str = Field(..., min_length=1, description="Content format, e.g. meme, vlog, tutorial, listicle")
    tone: str = Field(..., min_length=1, description="Content tone, e.g. humorous, technical, promotional")
    depth: DepthLevel = Field(..., description="Technical depth level: Beginner, Intermediate, Advanced")
    concept_tags: list[str] = Field(default_factory=list, description="Grounding technical concept tags")
    interest_evidence: list[InterestEvidence] = Field(
        default_factory=list,
        description="Atomic evidence of latent viewer characteristics implied by watching this reel",
    )


EXTRACTION_PROMPT_TEMPLATE = """You are ScrollSense's semantic signal extraction model.
Analyze the following short-form reel metadata and extract atomic semantic evidence about what watching this reel implies about the viewer.

REEL METADATA:
- Reel ID: {reel_id}
- Title: {title}
- Category: {category}
- Format: {format}
- Tone: {tone}
- Declared Depth: {depth}
- Concept Tags: {concept_tags}
- Transcript / Context: {transcript}

INSTRUCTIONS:
1. Distinguish between:
   - topic: normalized primary topic
   - format & tone: style attributes
   - depth: technical depth (Beginner, Intermediate, Advanced)
   - concept_tags: grounded technical keywords
   - interest_evidence: atomic evidence items.
2. Evidence Types:
   - "topic_implies_identity" / "professional_identity_signal": value MUST be one of {allowed_identities}
   - "career_stage_signal": value MUST be one of {allowed_career_stages}
   - "domain_signal": technical domain implied (e.g. java, backend, cloud_infrastructure, ai_engineering, gaming, hardware)
   - "goal_signal": viewer intent (e.g. career_prep, career_shortcuts)
3. Do NOT invent unsupported identities.
4. Do NOT attempt to produce final user persona or recommend content.
5. All evidence weights must be bounded floats in [0.0, 1.0].
6. Output ONLY valid structured JSON matching the requested schema.
"""


def format_extraction_prompt(
    reel: Reel,
    allowed_identities: set[str],
    allowed_career_stages: set[str],
) -> str:
    """Format structured extraction prompt for LLM provider."""
    return EXTRACTION_PROMPT_TEMPLATE.format(
        reel_id=reel.reel_id,
        title=reel.title,
        category=reel.category,
        format=reel.format or "general",
        tone=reel.tone or "informative",
        depth=reel.depth.value,
        concept_tags=", ".join(reel.concept_tags) if reel.concept_tags else "None",
        transcript=reel.transcript or "None",
        allowed_identities=sorted(list(allowed_identities)),
        allowed_career_stages=sorted(list(allowed_career_stages)),
    )
