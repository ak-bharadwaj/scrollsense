"""Inference policy configuration for deterministic InterestState aggregation."""

from pydantic import BaseModel, ConfigDict, Field


class InferencePolicy(BaseModel):
    """Configurable hyperparameters for deterministic InterestState inference."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    identity_evidence_scale: float = Field(
        default=0.6,
        ge=0.1,
        le=1.0,
        description="Scaling factor applied to individual reel evidence weights",
    )
    domain_evidence_scale: float = Field(
        default=0.6,
        ge=0.1,
        le=1.0,
        description="Scaling factor applied to domain evidence weights",
    )
    goal_evidence_scale: float = Field(
        default=0.7,
        ge=0.1,
        le=1.0,
        description="Scaling factor applied to goal evidence weights",
    )
    min_content_preference_observations: int = Field(
        default=2,
        ge=1,
        description="Minimum observations required before establishing a content preference",
    )
    max_weight_cap: float = Field(
        default=1.0,
        ge=0.5,
        le=1.0,
        description="Upper bound cap for aggregated weights",
    )
