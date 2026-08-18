"""Domain models for viewer persona and multi-dimensional interest state."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import DepthLevel


class InterestState(BaseModel):
    """Multi-dimensional interest state replacing single broad_interest string."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(..., min_length=1, description="Student / viewer identifier")
    professional_identity: dict[str, float] = Field(
        default_factory=dict,
        description="Inferred professional identity labels and weights, e.g. {'software_engineer': 0.86}",
    )
    domains: dict[str, float] = Field(
        default_factory=dict,
        description="Interest domains and weights, e.g. {'backend': 0.7, 'ai': 0.3}",
    )
    goals: dict[str, float] = Field(
        default_factory=dict,
        description="Viewer goals and weights, e.g. {'career_prep': 0.8}",
    )
    depth: dict[str, DepthLevel] = Field(
        default_factory=dict,
        description="Assessed depth per domain, e.g. {'systems': DepthLevel.BEGINNER}",
    )
    content_preference: dict[str, float] = Field(
        default_factory=dict,
        description="Content format preferences, e.g. {'humor': 0.6, 'tutorial': 0.7}",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="List of reel_ids driving the current interest state",
    )
    updated_at: datetime = Field(..., description="Timestamp of last state update")
