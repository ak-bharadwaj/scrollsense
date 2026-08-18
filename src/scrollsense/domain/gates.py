"""Domain models for the Three-Tier Gate: Safety, Quality, and Hype."""

from pydantic import BaseModel, ConfigDict, Field


class SafetyResult(BaseModel):
    """Hard pass/fail policy gate result."""

    model_config = ConfigDict(extra="forbid")

    passed: bool = Field(..., description="True unless prohibited/unsafe content")
    reason: str | None = Field(default=None, description="Explanation if rejected")


class QualityScore(BaseModel):
    """Continuous substance and conceptual depth score."""

    model_config = ConfigDict(extra="forbid")

    concept_anchor_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score indicating whether real, checkable concepts are named",
    )
    depth_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score indicating surface vs conceptual vs technical depth",
    )


class HypeScore(BaseModel):
    """Continuous hype and promotional language penalty."""

    model_config = ConfigDict(extra="forbid")

    pattern_penalty: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Penalty from cheap pattern regex (urgency, listicles, clickbait claims)",
    )
    promotional_language_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Continuous score of marketing/promotional tone",
    )
