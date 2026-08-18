"""Data structures for graph traversal results."""

from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import RelationType


class TraversalResult(BaseModel):
    """Result of a deterministic graph traversal path."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_node: str = Field(..., description="Origin starting node ID")
    destination_node: str = Field(..., description="Destination target node ID")
    graph_distance: int = Field(..., ge=1, description="Path length in hops (e.g. 1 or 2)")
    traversal_path: list[str] = Field(..., description="Ordered list of node IDs along the path")
    edge_weights: list[float] = Field(..., description="Weights of all edges along the path")
    relation_types: list[RelationType] = Field(..., description="Relation types along the path")
    cumulative_weight: float = Field(..., ge=0.0, le=1.0, description="Composite path weight (product of edge weights)")
