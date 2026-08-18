"""Domain models for viewer persona and multi-dimensional interest state."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from scrollsense.domain.enums import DepthLevel


class InterestState(BaseModel):
    """Multi-dimensional interest state replacing single broad_interest string."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(..., min_length=1, description="Student / viewer identifier")
    professional_identity: dict[str, float] = Field(
        default_factory=dict,
        description="Inferred professional identity labels and weights in [0, 1]",
    )
    domains: dict[str, float] = Field(
        default_factory=dict,
        description="Interest domains and weights in [0, 1]",
    )
    goals: dict[str, float] = Field(
        default_factory=dict,
        description="Viewer goals and weights in [0, 1]",
    )
    depth: dict[str, DepthLevel] = Field(
        default_factory=dict,
        description="Assessed depth per domain",
    )
    content_preference: dict[str, float] = Field(
        default_factory=dict,
        description="Content format preferences and weights in [0, 1]",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="List of reel_ids driving the current interest state",
    )
    updated_at: datetime = Field(..., description="Timestamp of last state update")

    @field_validator("professional_identity", "domains", "goals", "content_preference")
    @classmethod
    def validate_weights_in_unit_interval(cls, weights: dict[str, float]) -> dict[str, float]:
        """Ensure all dictionary numeric weights are bounded in [0.0, 1.0]."""
        for key, val in weights.items():
            if not isinstance(val, (int, float)):
                raise ValueError(f"Weight for '{key}' must be numeric, got {type(val).__name__}")
            if not (0.0 <= float(val) <= 1.0):
                raise ValueError(f"Weight for '{key}' must be in [0.0, 1.0], got {val}")
        return weights
