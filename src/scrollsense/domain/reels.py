"""Domain models for Reel content, signals, and interest evidence."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import DepthLevel, EvidenceType


class InterestEvidence(BaseModel):
    """Evidence extracted from a reel implying viewer characteristics."""

    model_config = ConfigDict(extra="forbid")

    evidence_type: EvidenceType = Field(
        ...,
        description="Typed category of evidence, e.g. career_stage_signal, professional_identity_signal",
    )
    value: str = Field(..., min_length=1, description="Extracted value, e.g. candidate, developer, software_engineer")
    weight: float | None = Field(default=None, ge=0.0, le=1.0, description="Optional weight or strength of this evidence")


class Reel(BaseModel):
    """Representation of raw short-form content in the system."""

    model_config = ConfigDict(extra="forbid")

    reel_id: str = Field(..., min_length=1, description="Unique identifier for the reel")
    title: str = Field(..., min_length=1, description="Title or headline of the reel")
    category: str = Field(..., min_length=1, description="Primary category / topic")
    format: str | None = Field(default=None, description="Format, e.g. meme, tutorial, vlog, interview_joke")
    tone: str | None = Field(default=None, description="Tone, e.g. humorous, technical, casual")
    depth: DepthLevel = Field(default=DepthLevel.BEGINNER, description="Technical depth level")
    concept_tags: list[str] = Field(default_factory=list, description="Grounding concept tags")
    transcript: str | None = Field(default=None, description="Optional transcript or caption text")


class ReelSignal(BaseModel):
    """Semantic signal layer for a reel, cached and versioned."""

    model_config = ConfigDict(extra="forbid")

    reel_id: str = Field(..., min_length=1, description="Target reel identifier")
    signal_version: str = Field(..., min_length=1, description="Extraction logic version")
    ontology_version: str = Field(..., min_length=1, description="Identity/Skill Graph schema version")
    model_version: str = Field(..., min_length=1, description="LLM/prompt version that produced this signal")
    generated_at: datetime = Field(..., description="Timestamp when signal was generated")
    topic: str = Field(..., min_length=1, description="Extracted core topic")
    format: str = Field(..., min_length=1, description="Extracted content format")
    tone: str = Field(..., min_length=1, description="Extracted tone")
    depth: DepthLevel = Field(..., description="Assessed technical depth level")
    concept_tags: list[str] = Field(default_factory=list, description="Extracted grounded concept tags")
    interest_evidence: list[InterestEvidence] = Field(
        default_factory=list,
        description="What watching this reel implies about the viewer",
    )
