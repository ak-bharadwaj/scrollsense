"""Graph loader and semantic validation adapter for Identity/Skill Graph."""

import json
from pathlib import Path
from typing import Any

from scrollsense.domain.enums import NodeType, RelationType
from scrollsense.domain.graph import IdentitySkillGraph
from scrollsense.graph.store import GraphStore


class GraphValidationError(ValueError):
    """Raised when an Identity/Skill Graph violates semantic integrity rules."""


class GraphLoader:
    """Loads and validates versioned Identity/Skill Graph JSON into a GraphStore."""

    @classmethod
    def load_from_json(cls, file_path: str | Path) -> GraphStore:
        """Load and strictly validate graph data from a JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Graph file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        return cls.load_from_dict(raw_data)

    @classmethod
    def load_from_dict(cls, data: dict[str, Any]) -> GraphStore:
        """Validate raw dictionary through Pydantic domain models and semantic checks."""
        # Extract core graph fields if metadata is bundled
        core_dict = {
            "version": data.get("version"),
            "nodes": data.get("nodes", []),
            "edges": data.get("edges", []),
        }

        # 1. Pydantic schema validation
        domain_graph = IdentitySkillGraph.model_validate(core_dict)

        # 2. Semantic integrity validation
        cls.validate_semantic_integrity(domain_graph)

        # 3. Build in-memory NetworkX GraphStore
        return GraphStore(domain_graph)

    @classmethod
    def validate_semantic_integrity(cls, graph: IdentitySkillGraph) -> None:
        """Verify that nodes are unique, edges are not dangling, and relation semantics are sound."""
        node_map: dict[str, NodeType] = {}
        for node in graph.nodes:
            if node.id in node_map:
                raise GraphValidationError(f"Duplicate node ID found: '{node.id}'")
            node_map[node.id] = node.category

        for edge in graph.edges:
            if edge.from_node not in node_map:
                raise GraphValidationError(
                    f"Dangling edge from non-existent node: '{edge.from_node}'"
                )
            if edge.to_node not in node_map:
                raise GraphValidationError(
                    f"Dangling edge to non-existent node: '{edge.to_node}'"
                )

            from_cat = node_map[edge.from_node]
            to_cat = node_map[edge.to_node]

            # Enforce semantic category constraints
            if edge.relation_type == RelationType.TOPIC_IMPLIES_IDENTITY:
                if from_cat != NodeType.TOPIC or to_cat != NodeType.PROFESSIONAL_IDENTITY:
                    raise GraphValidationError(
                        f"Relation '{edge.relation_type}' requires from:topic to:professional_identity, "
                        f"got {from_cat} -> {to_cat} ('{edge.from_node}' -> '{edge.to_node}')"
                    )

            elif edge.relation_type == RelationType.PROFESSIONAL_IDENTITY_SIGNAL:
                if from_cat != NodeType.TOPIC or to_cat != NodeType.PROFESSIONAL_IDENTITY:
                    raise GraphValidationError(
                        f"Relation '{edge.relation_type}' requires from:topic to:professional_identity, "
                        f"got {from_cat} -> {to_cat} ('{edge.from_node}' -> '{edge.to_node}')"
                    )

            elif edge.relation_type == RelationType.CAREER_STAGE_SIGNAL:
                if from_cat != NodeType.TOPIC or to_cat != NodeType.CAREER_STAGE:
                    raise GraphValidationError(
                        f"Relation '{edge.relation_type}' requires from:topic to:career_stage, "
                        f"got {from_cat} -> {to_cat} ('{edge.from_node}' -> '{edge.to_node}')"
                    )

            elif edge.relation_type == RelationType.IDENTITY_ADJACENT_SKILL:
                if from_cat != NodeType.PROFESSIONAL_IDENTITY or to_cat != NodeType.SKILL:
                    raise GraphValidationError(
                        f"Relation '{edge.relation_type}' requires from:professional_identity to:skill, "
                        f"got {from_cat} -> {to_cat} ('{edge.from_node}' -> '{edge.to_node}')"
                    )

            elif edge.relation_type == RelationType.ADJACENT_TO_ADJACENT:
                if from_cat != NodeType.SKILL or to_cat != NodeType.SKILL:
                    raise GraphValidationError(
                        f"Relation '{edge.relation_type}' requires from:skill to:skill, "
                        f"got {from_cat} -> {to_cat} ('{edge.from_node}' -> '{edge.to_node}')"
                    )

            elif edge.relation_type == RelationType.SKILL_IMPLIES_ROLE:
                if from_cat != NodeType.SKILL or to_cat != NodeType.PROFESSIONAL_IDENTITY:
                    raise GraphValidationError(
                        f"Relation '{edge.relation_type}' requires from:skill to:professional_identity, "
                        f"got {from_cat} -> {to_cat} ('{edge.from_node}' -> '{edge.to_node}')"
                    )
