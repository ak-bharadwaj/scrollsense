"""Policy configuration for diversity selection and final recommendation assembly."""

from pydantic import BaseModel, ConfigDict, Field


class SelectionPolicy(BaseModel):
    """Configurable hyperparameters for deterministic diversity and recommendation assembly."""

    model_config = ConfigDict(extra="forbid")

    max_recommendations: int = Field(default=1, ge=1, le=10, description="Number of recommendations to select")
    category_diversity_penalty: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Penalty applied to subsequent candidates sharing the same TechCategory",
    )
    high_confidence_evidence_threshold: int = Field(
        default=3,
        ge=1,
        description="Minimum supporting evidence count for High confidence",
    )
    high_confidence_weight_threshold: float = Field(
        default=0.75,
        ge=0.5,
        le=1.0,
        description="Minimum top identity weight for High confidence",
    )
    medium_confidence_weight_threshold: float = Field(
        default=0.45,
        ge=0.2,
        le=1.0,
        description="Minimum top identity weight for Medium confidence",
    )
    high_confidence_min_margin: float = Field(
        default=0.06,
        ge=0.0,
        le=1.0,
        description="Minimum final_score margin over runner-up for High confidence",
    )
    medium_confidence_min_margin: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Minimum final_score margin over runner-up for Medium confidence",
    )
    single_candidate_default_margin: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Assumed margin when only a single candidate exists in ranking",
    )
