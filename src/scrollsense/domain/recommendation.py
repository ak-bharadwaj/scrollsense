"""Domain models for internal and user-facing recommendation outputs."""

from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import ConfidenceBucket, DepthLevel, RetrievalSource, TechCategory
from scrollsense.domain.ranking import ObjectiveScores


class Recommendation(BaseModel):
    """Internal pipeline recommendation model with upstream traceability."""

    model_config = ConfigDict(extra="forbid")

    reel_id: str = Field(..., min_length=1, description="Recommended reel identifier")
    title: str = Field(..., min_length=1, description="Title of the recommended reel")
    final_score: float = Field(..., ge=0.0, le=1.0, description="Final ranked composite score in [0, 1]")
    confidence: ConfidenceBucket = Field(
        ...,
        description="Rule-derived confidence bucket: High, Medium, or Low",
    )
    retrieval_source: RetrievalSource = Field(
        ...,
        description="Typed retrieval source that generated this candidate",
    )
    traversal_path: list[str] = Field(
        default_factory=list,
        description="Graph traversal path that led to this recommendation",
    )
    objective_scores: ObjectiveScores | None = Field(
        default=None,
        description="Individual multi-objective component scores",
    )
    explanation: str = Field(
        ...,
        min_length=1,
        description="Traceable rationale explaining WHY based on latent identity and evidence",
    )
    evidence_reel_ids: list[str] = Field(
        default_factory=list,
        description="Reel IDs from user history that justified this recommendation",
    )


class RecommendationOutput(BaseModel):
    """User-facing recommendation output schema required by the problem statement."""

    model_config = ConfigDict(extra="forbid")

    current_reel: str = Field(..., min_length=1, description="Current / watched reel identifier or title")
    interest_detected: str = Field(..., min_length=1, description="Latent interest or professional identity inferred")
    why: str = Field(..., min_length=1, description="Explanation of why this interest was detected")
    recommended_tech_reel: str = Field(..., min_length=1, description="Recommended technical reel title or description")
    category: TechCategory = Field(..., description="Technical category of the recommended reel")
    why_this_recommendation: str = Field(
        ...,
        min_length=1,
        description="Explanation for why this specific recommendation fits the user and goal",
    )
    difficulty: DepthLevel = Field(..., description="Target depth / difficulty level")
    confidence: ConfidenceBucket = Field(..., description="Rule-derived confidence bucket: High, Medium, or Low")
