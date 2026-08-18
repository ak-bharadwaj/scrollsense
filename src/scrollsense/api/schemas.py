"""Pydantic schemas and API contracts for ScrollSense production endpoints."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.recommendation import RecommendationOutput


class FeedItemResponse(BaseModel):
    """Feed reel item representing playable content in the vertical feed."""

    model_config = ConfigDict(extra="forbid")

    reel_id: str = Field(..., min_length=1, description="Deterministic reel identifier")
    title: str = Field(..., min_length=1, description="Content title")
    creator: str | None = Field(default=None, description="Creator or channel attribution")
    category: str = Field(..., description="Topic category")
    difficulty: str = Field(..., description="Technical depth level (e.g., Beginner, Intermediate, Advanced)")
    thumbnail_url: str | None = Field(default=None, description="Poster or thumbnail image URL")
    video_url: str | None = Field(default=None, description="Streaming / media playback URL if media exists")
    duration_seconds: float | None = Field(default=None, description="Video playback duration in seconds")


class ReelDetailResponse(FeedItemResponse):
    """Full detail response for a single reel, including transcript and tags."""

    transcript: str | None = Field(default=None, description="Extracted or caption transcript")
    concept_tags: list[str] = Field(default_factory=list, description="Extracted technical concepts")
    license: str | None = Field(default=None, description="Content license basis")
    source_url: str | None = Field(default=None, description="Original source link")


class InteractionEvent(BaseModel):
    """User interaction event recorded during feed consumption."""

    model_config = ConfigDict(extra="forbid")

    reel_id: str = Field(..., min_length=1, description="Interacted reel identifier")
    event_type: str = Field(default="watch", description="Type of event (watch, like, skip, complete)")
    watched_seconds: float = Field(default=0.0, ge=0.0, description="Dwell time in seconds")
    completion_ratio: float = Field(default=1.0, ge=0.0, le=1.0, description="Fraction of reel watched")
    timestamp: datetime | None = Field(default=None, description="Client timestamp of event")


class RecommendRequest(BaseModel):
    """Stateless recommendation request payload containing interaction history."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(default="anonymous_student", min_length=1, max_length=64, description="Student session ID")
    history: list[InteractionEvent | str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Chronological interaction history as reel IDs or structured InteractionEvents",
    )


class ExplainabilityPayload(BaseModel):
    """Rich explainability data powering the interactive explainability drawer."""

    model_config = ConfigDict(extra="forbid")

    inferred_identities: dict[str, float] = Field(
        ...,
        description="Inferred latent professional identities and confidence weights for radar visualization",
    )
    domains_breakdown: dict[str, float] = Field(
        ...,
        description="Detected domain affinity strengths",
    )
    contributing_evidence: list[str] = Field(
        ...,
        description="Titles and IDs of watched reels that triggered this persona state",
    )
    graph_traversal: list[str] = Field(
        ...,
        description="Skill graph node traversal path justifying this recommendation",
    )
    raw_traces: dict[str, Any] = Field(
        default_factory=dict,
        description="Complete mathematical and ranking trace audit",
    )


class RecommendationResponse(BaseModel):
    """Official recommendation response returned to the frontend."""

    model_config = ConfigDict(extra="forbid")

    official_contract: RecommendationOutput = Field(
        ...,
        description="Exact 8-field required output contract required by problem statement",
    )
    recommended_reel: FeedItemResponse = Field(
        ...,
        description="Feed-compatible item for immediate video playback of recommendation",
    )
    explainability: ExplainabilityPayload = Field(
        ...,
        description="Traceable explainability and graph path payload",
    )
