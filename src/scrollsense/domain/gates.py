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

    @property
    def overall(self) -> float:
        """Composite continuous substance score in [0, 1]."""
        return round(0.5 * self.concept_anchor_score + 0.5 * self.depth_score, 4)


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

    @property
    def overall(self) -> float:
        """Composite continuous hype score in [0, 1]."""
        return round(0.6 * self.pattern_penalty + 0.4 * self.promotional_language_score, 4)


class GateResult(BaseModel):
    """Complete evaluation result for a candidate from the Three-Tier Gate."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., description="Target candidate reel ID")
    passed: bool = Field(..., description="True if candidate cleared safety, quality, and hype gates")
    safety: SafetyResult = Field(..., description="Safety evaluation result")
    quality: QualityScore = Field(..., description="Continuous substance and quality score")
    hype: HypeScore = Field(..., description="Continuous hype score")
    rejection_reason: str | None = Field(default=None, description="Explicit reason if rejected, else None")
