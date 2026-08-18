"""Data contracts for multi-objective ranking results and traces."""

from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.candidates import Candidate
from scrollsense.domain.gates import GateResult
from scrollsense.domain.ranking import ObjectiveScores
from scrollsense.ranking.weights import RankingWeights


class RankingTrace(BaseModel):
    """Detailed audit trace for a candidate's ranking evaluation."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., description="Target candidate reel ID")
    eligible: bool = Field(..., description="True if candidate passed gates and is eligible for ranking")
    objective_scores: ObjectiveScores = Field(..., description="Individual evaluated objective scores")
    weights: RankingWeights = Field(..., description="Weights applied during ranking")
    weighted_contributions: dict[str, float] = Field(
        ...,
        description="Individual weighted score contributions (weight * score)",
    )
    final_score: float = Field(..., ge=0.0, le=1.0, description="Composite final ranking score")
    gate_result: GateResult = Field(..., description="Result from the 3-Tier Gate evaluation")


class RankedCandidate(BaseModel):
    """A scored and ranked candidate ready for final recommendation."""

    model_config = ConfigDict(extra="forbid")

    candidate: Candidate = Field(..., description="Underlying candidate reel and provenance")
    scores: ObjectiveScores = Field(..., description="Component objective scores")
    final_score: float = Field(..., ge=0.0, le=1.0, description="Final composite ranking score")
    trace: RankingTrace = Field(..., description="Detailed audit trace")


class RankingResult(BaseModel):
    """Aggregated output of the ranking stage."""

    model_config = ConfigDict(extra="forbid")

    ranked_candidates: list[RankedCandidate] = Field(
        default_factory=list,
        description="Ordered list of eligible ranked candidates",
    )
    ineligible_traces: list[RankingTrace] = Field(
        default_factory=list,
        description="Audit traces for candidates rejected by safety or quality gates",
    )
