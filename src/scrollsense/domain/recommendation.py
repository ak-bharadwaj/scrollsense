"""Domain models for recommendation outputs."""

from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import ConfidenceBucket, RetrievalSource
from scrollsense.domain.ranking import ObjectiveScores


class Recommendation(BaseModel):
    """Final output recommendation schema with upstream traceability."""

    model_config = ConfigDict(extra="forbid")

    reel_id: str = Field(..., min_length=1, description="Recommended reel identifier")
    title: str = Field(..., min_length=1, description="Title of the recommended reel")
    final_score: float = Field(..., description="Final ranked composite score")
    confidence: ConfidenceBucket = Field(..., description="Calibrated confidence bucket: High, Medium, or Low")
    retrieval_source: RetrievalSource | str = Field(..., description="Retrieval source that generated this candidate")
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
        description="Traceable explanation explaining WHY based on latent identity and evidence",
    )
    evidence_reel_ids: list[str] = Field(
        default_factory=list,
        description="Reel IDs from user history that justified this recommendation",
    )
