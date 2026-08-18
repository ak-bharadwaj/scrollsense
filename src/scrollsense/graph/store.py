"""In-memory GraphStore backed by NetworkX for deterministic traversal."""

from typing import Any
import networkx as nx

from scrollsense.domain.enums import NodeType, RelationType
from scrollsense.domain.graph import GraphNode, IdentitySkillGraph
from scrollsense.graph.models import TraversalResult


class GraphStore:
    """In-memory Identity/Skill Graph store backed by a directed NetworkX graph."""

    def __init__(self, domain_graph: IdentitySkillGraph) -> None:
        self.version = domain_graph.version
        self._domain_graph = domain_graph
        self._nx_graph: nx.DiGraph[Any] = nx.DiGraph()
        self._nodes_by_id: dict[str, GraphNode] = {}
        self._build_graph(domain_graph)

    def _build_graph(self, domain_graph: IdentitySkillGraph) -> None:
        """Populate NetworkX graph with domain nodes and weighted directed edges."""
        for node in domain_graph.nodes:
            self._nodes_by_id[node.id] = node
            self._nx_graph.add_node(
                node.id,
                category=node.category,
                label=node.label or node.id,
            )

        for edge in domain_graph.edges:
            self._nx_graph.add_edge(
                edge.from_node,
                edge.to_node,
                relation_type=edge.relation_type,
                weight=edge.weight,
            )

    @property
    def node_count(self) -> int:
        """Total number of nodes in the graph."""
        return self._nx_graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        """Total number of edges in the graph."""
        return self._nx_graph.number_of_edges()

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve typed GraphNode by ID if it exists."""
        return self._nodes_by_id.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """Check if node ID exists in the graph."""
        return node_id in self._nodes_by_id

    def traverse_1_hop_identity_adjacent(self, identity_node_id: str) -> list[TraversalResult]:
        """Traverse Source B: 1-hop from a professional_identity node to adjacent skills.

        Determinism Rule:
        Results are ordered descending by cumulative edge weight, and secondarily
        alphabetically by destination_node ID for deterministic tie-breaking.
        """
        if not self.has_node(identity_node_id):
            raise KeyError(f"Identity node '{identity_node_id}' does not exist in graph")

        node = self._nodes_by_id[identity_node_id]
        if node.category != NodeType.PROFESSIONAL_IDENTITY:
            raise ValueError(
                f"Source node '{identity_node_id}' has category '{node.category}', "
                f"expected '{NodeType.PROFESSIONAL_IDENTITY}'"
            )

        results: list[TraversalResult] = []
        for successor_id in self._nx_graph.successors(identity_node_id):
            edge_data = self._nx_graph[identity_node_id][successor_id]
            relation: RelationType = edge_data["relation_type"]
            weight: float = edge_data["weight"]
            target_node = self._nodes_by_id[successor_id]

            if relation == RelationType.IDENTITY_ADJACENT_SKILL and target_node.category == NodeType.SKILL:
                results.append(
                    TraversalResult(
                        source_node=identity_node_id,
                        destination_node=successor_id,
                        graph_distance=1,
                        traversal_path=[identity_node_id, successor_id],
                        edge_weights=[weight],
                        relation_types=[relation],
                        cumulative_weight=weight,
                    )
                )

        # Deterministic ordering: descending weight, ascending destination_node
        results.sort(key=lambda r: (-r.cumulative_weight, r.destination_node))
        return results

    def traverse_2_hop_boundary_exploration(self, identity_node_id: str) -> list[TraversalResult]:
        """Traverse Source C: 2-hop boundary exploration (identity -> skill -> adjacent skill).

        Determinism Rule:
        Results are ordered descending by composite path weight (w1 * w2),
        secondarily alphabetically by destination_node ID, and tertiarily by
        intermediate node ID.
        """
        if not self.has_node(identity_node_id):
            raise KeyError(f"Identity node '{identity_node_id}' does not exist in graph")

        node = self._nodes_by_id[identity_node_id]
        if node.category != NodeType.PROFESSIONAL_IDENTITY:
            raise ValueError(
                f"Source node '{identity_node_id}' has category '{node.category}', "
                f"expected '{NodeType.PROFESSIONAL_IDENTITY}'"
            )

        results: list[TraversalResult] = []

        # 1st hop: identity -> intermediate skill
        for intermediate_id in self._nx_graph.successors(identity_node_id):
            hop1_edge = self._nx_graph[identity_node_id][intermediate_id]
            hop1_rel: RelationType = hop1_edge["relation_type"]
            w1: float = hop1_edge["weight"]
            intermediate_node = self._nodes_by_id[intermediate_id]

            if hop1_rel != RelationType.IDENTITY_ADJACENT_SKILL or intermediate_node.category != NodeType.SKILL:
                continue

            # 2nd hop: intermediate skill -> boundary skill
            for destination_id in self._nx_graph.successors(intermediate_id):
                if destination_id == identity_node_id or destination_id == intermediate_id:
                    continue

                hop2_edge = self._nx_graph[intermediate_id][destination_id]
                hop2_rel: RelationType = hop2_edge["relation_type"]
                w2: float = hop2_edge["weight"]
                dest_node = self._nodes_by_id[destination_id]

                if hop2_rel == RelationType.ADJACENT_TO_ADJACENT and dest_node.category == NodeType.SKILL:
                    cum_weight = round(w1 * w2, 6)
                    results.append(
                        TraversalResult(
                            source_node=identity_node_id,
                            destination_node=destination_id,
                            graph_distance=2,
                            traversal_path=[identity_node_id, intermediate_id, destination_id],
                            edge_weights=[w1, w2],
                            relation_types=[hop1_rel, hop2_rel],
                            cumulative_weight=cum_weight,
                        )
                    )

        # Deterministic ordering: descending cumulative weight, ascending destination ID, ascending intermediate ID
        results.sort(key=lambda r: (-r.cumulative_weight, r.destination_node, r.traversal_path[1]))
        return results
