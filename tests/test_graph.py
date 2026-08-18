"""Unit tests for Identity/Skill Graph loader, validation adapter, and deterministic traversal."""

from pathlib import Path
import pytest
from pydantic import ValidationError

from scrollsense.domain.enums import NodeType, RelationType
from scrollsense.graph import GraphLoader, GraphStore, GraphValidationError

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GRAPH_PATH = DATA_DIR / "identity_skill_graph.json"


@pytest.fixture
def canonical_store() -> GraphStore:
    """Fixture providing loaded canonical GraphStore."""
    return GraphLoader.load_from_json(GRAPH_PATH)


def test_graph_loads_successfully(canonical_store: GraphStore):
    """Verify canonical graph loads cleanly into GraphStore with expected counts."""
    assert canonical_store.node_count >= 20
    assert canonical_store.edge_count >= 20
    assert canonical_store.has_node("software_engineer")
    assert canonical_store.has_node("gamer")


def test_swe_1_hop_traversal(canonical_store: GraphStore):
    """Verify 1-hop traversal for software_engineer yields System Design, DSA, Cloud, Cybersecurity, AI."""
    results = canonical_store.traverse_1_hop_identity_adjacent("software_engineer")
    destinations = [r.destination_node for r in results]

    expected = ["system_design", "dsa", "cloud_infrastructure", "cybersecurity", "ai_engineering"]
    for skill in expected:
        assert skill in destinations, f"Missing 1-hop adjacent skill '{skill}' from software_engineer"

    for r in results:
        assert r.source_node == "software_engineer"
        assert r.graph_distance == 1
        assert len(r.traversal_path) == 2
        assert r.traversal_path[0] == "software_engineer"
        assert r.traversal_path[1] == r.destination_node
        assert len(r.edge_weights) == 1
        assert 0.0 <= r.cumulative_weight <= 1.0
        assert r.relation_types == [RelationType.IDENTITY_ADJACENT_SKILL]


def test_swe_2_hop_boundary_traversal(canonical_store: GraphStore):
    """Verify 2-hop boundary traversal from SWE reaches Distributed Caching and Tree Algorithms."""
    results = canonical_store.traverse_2_hop_boundary_exploration("software_engineer")
    destinations = [r.destination_node for r in results]

    assert "distributed_caching" in destinations
    assert "tree_algorithms" in destinations
    assert "kubernetes_orchestration" in destinations
    assert "oauth_security" in destinations
    assert "transformer_architecture" in destinations

    # Check path and weight structure for distributed caching
    caching_res = next(r for r in results if r.destination_node == "distributed_caching")
    assert caching_res.source_node == "software_engineer"
    assert caching_res.graph_distance == 2
    assert caching_res.traversal_path == ["software_engineer", "system_design", "distributed_caching"]
    assert len(caching_res.edge_weights) == 2
    assert caching_res.edge_weights == [0.85, 0.80]
    assert caching_res.cumulative_weight == round(0.85 * 0.80, 6)
    assert caching_res.relation_types == [
        RelationType.IDENTITY_ADJACENT_SKILL,
        RelationType.ADJACENT_TO_ADJACENT,
    ]

    # Check path and weight structure for tree algorithms
    tree_res = next(r for r in results if r.destination_node == "tree_algorithms")
    assert tree_res.traversal_path == ["software_engineer", "dsa", "tree_algorithms"]
    assert tree_res.graph_distance == 2
    assert tree_res.edge_weights == [0.80, 0.80]
    assert tree_res.cumulative_weight == round(0.80 * 0.80, 6)


def test_gamer_1_hop_traversal(canonical_store: GraphStore):
    """Verify gamer identity has 1-hop traversal to esports_strategy."""
    results = canonical_store.traverse_1_hop_identity_adjacent("gamer")
    assert len(results) == 1
    assert results[0].destination_node == "esports_strategy"
    assert results[0].graph_distance == 1
    assert results[0].traversal_path == ["gamer", "esports_strategy"]
    assert results[0].cumulative_weight == 0.70


def test_traversal_determinism(canonical_store: GraphStore):
    """Verify repeated traversal calls yield identical ordering and values."""
    res_1 = canonical_store.traverse_1_hop_identity_adjacent("software_engineer")
    res_2 = canonical_store.traverse_1_hop_identity_adjacent("software_engineer")
    assert [r.model_dump() for r in res_1] == [r.model_dump() for r in res_2]

    hop2_1 = canonical_store.traverse_2_hop_boundary_exploration("software_engineer")
    hop2_2 = canonical_store.traverse_2_hop_boundary_exploration("software_engineer")
    assert [r.model_dump() for r in hop2_1] == [r.model_dump() for r in hop2_2]


def test_traversal_invalid_origin_category(canonical_store: GraphStore):
    """Verify traversal fails when called on a non-identity node or missing node."""
    with pytest.raises(ValueError) as exc:
        canonical_store.traverse_1_hop_identity_adjacent("system_design")  # skill, not identity
    assert "expected 'professional_identity'" in str(exc.value)

    with pytest.raises(KeyError):
        canonical_store.traverse_1_hop_identity_adjacent("non_existent_node")


def test_loader_rejects_dangling_edge():
    """Verify loader rejects graphs with dangling edge references."""
    data = {
        "version": "1.0",
        "nodes": [{"id": "n1", "category": "topic"}],
        "edges": [
            {
                "from_node": "n1",
                "to_node": "missing_node",
                "relation_type": "topic_implies_identity",
                "weight": 0.5,
            }
        ],
    }
    with pytest.raises(GraphValidationError) as exc:
        GraphLoader.load_from_dict(data)
    assert "Dangling edge to non-existent node" in str(exc.value)


def test_loader_rejects_duplicate_nodes():
    """Verify loader rejects graphs with duplicate node IDs."""
    data = {
        "version": "1.0",
        "nodes": [
            {"id": "n1", "category": "topic"},
            {"id": "n1", "category": "skill"},
        ],
        "edges": [],
    }
    with pytest.raises(GraphValidationError) as exc:
        GraphLoader.load_from_dict(data)
    assert "Duplicate node ID found" in str(exc.value)


def test_loader_rejects_invalid_relation_category_semantics():
    """Verify loader rejects semantically incompatible node-relation pairs."""
    data = {
        "version": "1.0",
        "nodes": [
            {"id": "n1", "category": "skill"},
            {"id": "n2", "category": "skill"},
        ],
        "edges": [
            {
                "from_node": "n1",
                "to_node": "n2",
                "relation_type": "topic_implies_identity",  # Requires topic -> professional_identity
                "weight": 0.5,
            }
        ],
    }
    with pytest.raises(GraphValidationError) as exc:
        GraphLoader.load_from_dict(data)
    assert "requires from:topic to:professional_identity" in str(exc.value)


def test_loader_rejects_invalid_weights():
    """Verify loader rejects out-of-bounds edge weights at schema validation level."""
    data = {
        "version": "1.0",
        "nodes": [
            {"id": "n1", "category": "topic"},
            {"id": "n2", "category": "professional_identity"},
        ],
        "edges": [
            {
                "from_node": "n1",
                "to_node": "n2",
                "relation_type": "topic_implies_identity",
                "weight": 1.5,
            }
        ],
    }
    with pytest.raises(ValidationError):
        GraphLoader.load_from_dict(data)
