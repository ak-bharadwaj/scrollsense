"""Domain models for multi-objective ranking scores."""

from pydantic import BaseModel, ConfigDict, Field


class ObjectiveScores(BaseModel):
    """Component scores evaluated during multi-objective ranking."""

    model_config = ConfigDict(extra="forbid")

    topical_fit: float = Field(..., description="Topical alignment with interest state domains")
    difficulty_match: float = Field(..., description="Difficulty alignment with student depth")
    career_relevance: float = Field(..., description="Contextual career relevance based on goals and depth")
    novelty: float = Field(..., description="Novelty/diversity term relative to recent history")
    quality: float = Field(..., description="Concept anchor / quality contribution")
    hype_penalty: float = Field(..., description="Penalty term for promotional/hype language")
    final_score: float | None = Field(default=None, description="Calculated weighted final score")
