"""Configurable weights for multi-objective candidate ranking."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RankingWeights(BaseModel):
    """Configurable weights for the 6 ranking objectives, strictly validated."""

    model_config = ConfigDict(extra="forbid")

    topical_fit: float = Field(default=0.20, ge=0.0, le=1.0, description="Weight for topical fit")
    difficulty_match: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for difficulty alignment")
    career_relevance: float = Field(default=0.25, ge=0.0, le=1.0, description="Weight for contextual career relevance")
    novelty: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for novelty / exploration")
    quality: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for continuous substance / quality score")
    hype_penalty: float = Field(default=0.10, ge=0.0, le=1.0, description="Penalty weight for hype / promotional language")

    @model_validator(mode="after")
    def validate_positive_weights(self) -> "RankingWeights":
        """Verify that at least one positive weight is non-zero."""
        pos_sum = (
            self.topical_fit
            + self.difficulty_match
            + self.career_relevance
            + self.novelty
            + self.quality
        )
        if pos_sum <= 0.0:
            raise ValueError("Sum of positive objective weights must be greater than 0.0")
        return self
