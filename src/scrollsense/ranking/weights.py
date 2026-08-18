"""Configurable weights for multi-objective candidate ranking."""

import math
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RankingWeights(BaseModel):
    """Configurable weights for the 6 normalized heuristic ranking objectives, strictly validated."""

    model_config = ConfigDict(extra="forbid")

    topical_fit: float = Field(default=0.20, ge=0.0, le=1.0, description="Weight for topical fit")
    difficulty_match: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for difficulty alignment")
    career_relevance: float = Field(default=0.25, ge=0.0, le=1.0, description="Weight for contextual career relevance")
    novelty: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for novelty / exploration")
    quality: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for continuous substance / quality score")
    hype_penalty: float = Field(default=0.10, ge=0.0, le=1.0, description="Penalty weight for hype / promotional language")

    @model_validator(mode="after")
    def validate_weight_sum(self) -> "RankingWeights":
        """Verify that all 6 weights sum to 1.0 within a floating-point tolerance."""
        total_sum = (
            self.topical_fit
            + self.difficulty_match
            + self.career_relevance
            + self.novelty
            + self.quality
            + self.hype_penalty
        )
        if not math.isclose(total_sum, 1.0, rel_tol=1e-5, abs_tol=1e-5):
            raise ValueError(
                f"Total sum of ranking weights must equal 1.0 within floating-point tolerance, got {total_sum:.4f}"
            )
        return self
