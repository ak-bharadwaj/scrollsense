"""Domain models for retrieved candidates."""

from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import RetrievalSource


class Candidate(BaseModel):
    """Candidate reel retrieved through one of the multi-source retrieval paths."""

    model_config = ConfigDict(extra="forbid")

    reel_id: str = Field(..., min_length=1, description="Identifier of the candidate reel")
    source: RetrievalSource = Field(..., description="Primary retrieval source that generated this candidate")
    matched_node: str | None = Field(default=None, description="Graph node matched during retrieval")
    graph_distance: int | None = Field(default=None, ge=0, description="Graph distance from origin node (e.g. 1 for Source B, 2 for Source C)")
    traversal_path: list[str] = Field(
        default_factory=list,
        description="Sequence of node IDs traversed from origin to destination",
    )
    initial_score: float | None = Field(
        default=None,
        description="Initial score from cheap ranking before deep multi-objective ranking",
    )
    contributing_sources: list[RetrievalSource] = Field(
        default_factory=list,
        description="All retrieval sources that independently retrieved this candidate",
    )
    contributing_paths: list[list[str]] = Field(
        default_factory=list,
        description="All distinct traversal paths that led to this candidate",
    )
