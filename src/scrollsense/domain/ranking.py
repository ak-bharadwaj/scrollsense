"""Domain models for multi-objective ranking scores."""

from pydantic import BaseModel, ConfigDict, Field


class ObjectiveScores(BaseModel):
    """Component scores evaluated during multi-objective ranking, each bounded in [0, 1]."""

    model_config = ConfigDict(extra="forbid")

    topical_fit: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Topical alignment with interest state domains in [0, 1]",
    )
    difficulty_match: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Difficulty alignment with student depth in [0, 1]",
    )
    career_relevance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Contextual career relevance based on goals and depth in [0, 1]",
    )
    novelty: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Novelty/diversity term relative to recent history in [0, 1]",
    )
    quality: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Concept anchor / substance score in [0, 1]",
    )
    hype_penalty: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Penalty term for promotional/hype language in [0, 1]",
    )
    final_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Calculated weighted final score in [0, 1]",
    )
