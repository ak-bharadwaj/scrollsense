"""Domain models for the Identity/Skill Graph."""

from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import NodeType, RelationType


class GraphNode(BaseModel):
    """Typed node in the Identity/Skill Graph."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, description="Unique node identifier, e.g. software_engineer, java")
    category: NodeType = Field(..., description="Typed node category")
    label: str | None = Field(default=None, description="Human-readable label")


class GraphEdge(BaseModel):
    """Directed, weighted edge in the Identity/Skill Graph."""

    model_config = ConfigDict(extra="forbid")

    from_node: str = Field(..., min_length=1, description="Origin node ID")
    to_node: str = Field(..., min_length=1, description="Destination node ID")
    relation_type: RelationType = Field(
        ...,
        description="Typed relation type, e.g. topic_implies_identity, identity_adjacent_skill",
    )
    weight: float = Field(..., ge=0.0, le=1.0, description="Edge weight / confidence")


class IdentitySkillGraph(BaseModel):
    """Versioned, explicit, hand-authored Identity/Skill Graph."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(..., min_length=1, description="Graph schema/ontology version")
    nodes: list[GraphNode] = Field(default_factory=list, description="All nodes in the graph")
    edges: list[GraphEdge] = Field(default_factory=list, description="All directed edges in the graph")
