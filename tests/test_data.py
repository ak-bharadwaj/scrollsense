"""Data validation tests for ScrollSense v4 datasets and Identity/Skill Graph."""

import json
from pathlib import Path

from scrollsense.domain import (
    IdentitySkillGraph,
    NodeType,
    Reel,
    RelationType,
    TechCategory,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_inputs_json_schema_and_exact_count():
    """Verify data/inputs.json contains exactly 8 reels across the required 8 categories."""
    inputs_path = DATA_DIR / "inputs.json"
    assert inputs_path.exists(), "data/inputs.json does not exist"

    with open(inputs_path, "r", encoding="utf-8") as f:
        inputs_data = json.load(f)

    assert isinstance(inputs_data, list)
    assert len(inputs_data) == 8, f"Expected exactly 8 input reels, found {len(inputs_data)}"

    required_categories = {
        "entertainment",
        "gaming",
        "coding",
        "AI",
        "gadgets",
        "career",
        "programming_memes",
        "tech_news",
    }

    found_categories = set()
    input_ids = set()
    for item in inputs_data:
        reel = Reel.model_validate(item)
        assert reel.reel_id not in input_ids, f"Duplicate input reel_id: {reel.reel_id}"
        input_ids.add(reel.reel_id)
        found_categories.add(reel.category)

    assert found_categories == required_categories, f"Mismatch in required input categories: {found_categories ^ required_categories}"


def test_candidates_json_schema_and_id_uniqueness():
    """Verify data/candidates.json reels conform to Reel schema and have no overlap with inputs.json."""
    inputs_path = DATA_DIR / "inputs.json"
    candidates_path = DATA_DIR / "candidates.json"
    assert candidates_path.exists(), "data/candidates.json does not exist"

    with open(inputs_path, "r", encoding="utf-8") as f:
        inputs_data = json.load(f)
    input_ids = {r["reel_id"] for r in inputs_data}

    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates_data = json.load(f)

    assert isinstance(candidates_data, list)
    assert len(candidates_data) >= 5, "Expected candidate reels in candidate pool"

    candidate_ids = set()
    for item in candidates_data:
        reel = Reel.model_validate(item)
        assert reel.reel_id not in candidate_ids, f"Duplicate candidate reel_id: {reel.reel_id}"
        assert reel.reel_id not in input_ids, f"Reel ID {reel.reel_id} appears in both inputs and candidates"
        candidate_ids.add(reel.reel_id)


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


def test_identity_skill_graph_schema_integrity_and_semantics():
    """Verify identity_skill_graph.json conforms to contracts, has valid references and category compatibility."""
    graph_path = DATA_DIR / "identity_skill_graph.json"
    assert graph_path.exists(), "data/identity_skill_graph.json does not exist"

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    core_graph_dict = {
        "version": graph_data["version"],
        "nodes": graph_data["nodes"],
        "edges": graph_data["edges"],
    }
    graph = IdentitySkillGraph.model_validate(core_graph_dict)
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    node_map: dict[str, NodeType] = {}
    for node in graph.nodes:
        assert node.id not in node_map, f"Duplicate graph node ID: {node.id}"
        node_map[node.id] = node.category

    # Verify edge referential integrity, weight bounds, and semantic category compatibility
    for edge in graph.edges:
        assert edge.from_node in node_map, f"Edge from_node '{edge.from_node}' does not exist in nodes list"
        assert edge.to_node in node_map, f"Edge to_node '{edge.to_node}' does not exist in nodes list"
        assert 0.0 <= edge.weight <= 1.0, f"Edge weight {edge.weight} outside [0, 1]"

        from_cat = node_map[edge.from_node]
        to_cat = node_map[edge.to_node]

        if edge.relation_type == RelationType.TOPIC_IMPLIES_IDENTITY:
            assert from_cat == NodeType.TOPIC, f"topic_implies_identity from_node must be topic, got {from_cat}"
            assert to_cat == NodeType.PROFESSIONAL_IDENTITY, f"topic_implies_identity to_node must be professional_identity, got {to_cat}"

        elif edge.relation_type == RelationType.PROFESSIONAL_IDENTITY_SIGNAL:
            assert from_cat == NodeType.TOPIC, f"professional_identity_signal from_node must be topic, got {from_cat}"
            assert to_cat == NodeType.PROFESSIONAL_IDENTITY, f"professional_identity_signal to_node must be professional_identity, got {to_cat}"

        elif edge.relation_type == RelationType.CAREER_STAGE_SIGNAL:
            assert from_cat == NodeType.TOPIC, f"career_stage_signal from_node must be topic, got {from_cat}"
            assert to_cat == NodeType.CAREER_STAGE, f"career_stage_signal to_node must be career_stage, got {to_cat}"

        elif edge.relation_type == RelationType.IDENTITY_ADJACENT_SKILL:
            assert from_cat == NodeType.PROFESSIONAL_IDENTITY, f"identity_adjacent_skill from_node must be professional_identity, got {from_cat}"
            assert to_cat == NodeType.SKILL, f"identity_adjacent_skill to_node must be skill, got {to_cat}"

        elif edge.relation_type == RelationType.ADJACENT_TO_ADJACENT:
            assert from_cat == NodeType.SKILL, f"adjacent_to_adjacent from_node must be skill, got {from_cat}"
            assert to_cat == NodeType.SKILL, f"adjacent_to_adjacent to_node must be skill, got {to_cat}"

        elif edge.relation_type == RelationType.SKILL_IMPLIES_ROLE:
            assert from_cat == NodeType.SKILL, f"skill_implies_role from_node must be skill, got {from_cat}"
            assert to_cat == NodeType.PROFESSIONAL_IDENTITY, f"skill_implies_role to_node must be professional_identity, got {to_cat}"


def test_trap_test_cases_integrity():
    """Verify data/trap_test_cases.json references existing reels and valid schema."""
    trap_path = DATA_DIR / "trap_test_cases.json"
    inputs_path = DATA_DIR / "inputs.json"
    candidates_path = DATA_DIR / "candidates.json"

    with open(inputs_path, "r", encoding="utf-8") as f:
        inputs_data = json.load(f)
    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates_data = json.load(f)

    all_reel_ids = {r["reel_id"] for r in inputs_data} | {r["reel_id"] for r in candidates_data}

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
            assert r_id in all_reel_ids, f"Case {case_id} references non-existent watched reel: {r_id}"

        reject_reels = case.get("should_reject_reels", [])
        for r_id in reject_reels:
            assert r_id in all_reel_ids, f"Case {case_id} references non-existent should_reject_reel: {r_id}"

        for cat in case.get("expected_recommendation_categories", []):
            assert cat in [t.value for t in TechCategory], f"Invalid category {cat} in case {case_id}"


def test_trap_case_heterogeneous_watch_history_presence():
    """Verify the 4 canonical trap reels are present in data/inputs.json."""
    with open(DATA_DIR / "inputs.json", "r", encoding="utf-8") as f:
        inputs_map = {r["reel_id"]: r for r in json.load(f)}

    canonical_trap_reels = [
        "reel_java_meme",
        "reel_swe_lifestyle",
        "reel_interview_joke",
        "reel_laptop_comparison",
    ]
    for r_id in canonical_trap_reels:
        assert r_id in inputs_map, f"Missing canonical trap reel in inputs.json: {r_id}"
