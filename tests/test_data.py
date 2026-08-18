"""Data validation tests for ScrollSense v4 datasets and Identity/Skill Graph."""

import json
from pathlib import Path
import pytest

from scrollsense.domain import (
    GraphEdge,
    GraphNode,
    IdentitySkillGraph,
    Reel,
    TechCategory,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_reels_json_schema():
    """Verify all reels in data/reels.json strictly conform to the Reel domain model."""
    reels_path = DATA_DIR / "reels.json"
    assert reels_path.exists(), "data/reels.json does not exist"

    with open(reels_path, "r", encoding="utf-8") as f:
        reels_data = json.load(f)

    assert isinstance(reels_data, list)
    assert len(reels_data) >= 8, "Expected at least 8 sample reels"

    reel_ids = set()
    for item in reels_data:
        reel = Reel.model_validate(item)
        assert reel.reel_id not in reel_ids, f"Duplicate reel_id found: {reel.reel_id}"
        reel_ids.add(reel.reel_id)


def test_taxonomy_json_valid():
    """Verify taxonomy.json categories match TechCategory enum values without dangling entries."""
    taxonomy_path = DATA_DIR / "taxonomy.json"
    assert taxonomy_path.exists(), "data/taxonomy.json does not exist"

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        taxonomy_data = json.load(f)

    categories = taxonomy_data.get("categories", [])
    assert len(categories) == len(TechCategory), "Taxonomy count must match TechCategory count"

    defined_ids = {c["id"] for c in categories}
    enum_ids = {t.value for t in TechCategory}
    assert defined_ids == enum_ids, f"Mismatch in taxonomy categories: {defined_ids ^ enum_ids}"


def test_identity_skill_graph_schema_and_integrity():
    """Verify data/identity_skill_graph.json conforms to contracts and has no dangling references."""
    graph_path = DATA_DIR / "identity_skill_graph.json"
    assert graph_path.exists(), "data/identity_skill_graph.json does not exist"

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    # Filter out metadata if present before validating core graph
    core_graph_dict = {
        "version": graph_data["version"],
        "nodes": graph_data["nodes"],
        "edges": graph_data["edges"],
    }
    graph = IdentitySkillGraph.model_validate(core_graph_dict)
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    node_ids = set()
    for node in graph.nodes:
        assert node.id not in node_ids, f"Duplicate graph node ID: {node.id}"
        node_ids.add(node.id)

    # Verify no dangling edges & valid weights
    for edge in graph.edges:
        assert edge.from_node in node_ids, f"Edge from_node '{edge.from_node}' does not exist in nodes list"
        assert edge.to_node in node_ids, f"Edge to_node '{edge.to_node}' does not exist in nodes list"
        assert 0.0 <= edge.weight <= 1.0, f"Edge weight {edge.weight} outside [0, 1]"


def test_trap_test_cases_integrity():
    """Verify data/trap_test_cases.json references existing reels and valid schema."""
    trap_path = DATA_DIR / "trap_test_cases.json"
    reels_path = DATA_DIR / "reels.json"
    assert trap_path.exists(), "data/trap_test_cases.json does not exist"

    with open(reels_path, "r", encoding="utf-8") as f:
        reels_data = json.load(f)
    valid_reel_ids = {r["reel_id"] for r in reels_data}

    with open(trap_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    assert isinstance(cases, list)
    assert len(cases) >= 3, "Expected at least 3 trap test cases"

    case_ids = set()
    for case in cases:
        case_id = case["case_id"]
        assert case_id not in case_ids, f"Duplicate case_id: {case_id}"
        case_ids.add(case_id)

        watched = case.get("watched_reel_ids", [])
        assert len(watched) > 0, f"Case {case_id} has no watched reels"
        for r_id in watched:
            assert r_id in valid_reel_ids, f"Case {case_id} references non-existent watched reel: {r_id}"

        reject_reels = case.get("should_reject_reels", [])
        for r_id in reject_reels:
            assert r_id in valid_reel_ids, f"Case {case_id} references non-existent should_reject_reel: {r_id}"

        # Expected categories must match TechCategory values
        for cat in case.get("expected_recommendation_categories", []):
            assert cat in [t.value for t in TechCategory], f"Invalid category {cat} in case {case_id}"


def test_trap_case_heterogeneous_watch_history_presence():
    """Verify the 4 canonical trap reels are present in data/reels.json."""
    with open(DATA_DIR / "reels.json", "r", encoding="utf-8") as f:
        reels = {r["reel_id"]: r for r in json.load(f)}

    canonical_trap_reels = [
        "reel_java_meme",
        "reel_swe_lifestyle",
        "reel_interview_joke",
        "reel_laptop_comparison",
    ]
    for r_id in canonical_trap_reels:
        assert r_id in reels, f"Missing canonical trap reel: {r_id}"
