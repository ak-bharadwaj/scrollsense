"""Unit tests for deterministic multi-source candidate retrieval in ScrollSense v4."""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from scrollsense.domain.enums import DepthLevel, RetrievalSource
from scrollsense.domain.persona import InterestState
from scrollsense.graph import GraphLoader
from scrollsense.retrieval import CandidateRepository, MultiSourceRetriever

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GRAPH_PATH = DATA_DIR / "identity_skill_graph.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"


@pytest.fixture
def retriever() -> MultiSourceRetriever:
    """Fixture providing initialized MultiSourceRetriever with canonical graph and candidates."""
    graph_store = GraphLoader.load_from_json(GRAPH_PATH)
    candidate_repo = CandidateRepository.load_from_json(CANDIDATES_PATH)
    return MultiSourceRetriever(candidate_repo, graph_store)


def test_swe_identity_retrieves_hld_candidate_via_source_b(retriever: MultiSourceRetriever):
    """Test 1: SWE identity retrieves HLD candidate through Source B."""
    state = InterestState(
        student_id="student_swe",
        professional_identity={"software_engineer": 0.85},
        domains={},
        goals={"career_prep": 0.9},
        depth={"system_design": DepthLevel.BEGINNER},
        content_preference={},
        evidence=["reel_java_meme", "reel_swe_lifestyle"],
        updated_at=datetime.now(timezone.utc),
    )

    candidates_b = retriever.retrieve_source_b_identity_adjacent(state)
    candidate_ids = [c.reel_id for c in candidates_b]

    assert "reel_hld_caching" in candidate_ids
    hld_cand = next(c for c in candidates_b if c.reel_id == "reel_hld_caching")
    assert hld_cand.source == RetrievalSource.SOURCE_B_IDENTITY_ADJACENT
    assert hld_cand.graph_distance == 1
    assert hld_cand.traversal_path == ["software_engineer", "system_design"]
    assert hld_cand.matched_node == "system_design"


def test_swe_identity_retrieves_dsa_cloud_cybersecurity(retriever: MultiSourceRetriever):
    """Test 2: SWE identity retrieves DSA, Cloud, and Cybersecurity candidates through Source B."""
    state = InterestState(
        student_id="student_swe",
        professional_identity={"software_engineer": 0.85},
        domains={},
        goals={},
        depth={},
        content_preference={},
        evidence=[],
        updated_at=datetime.now(timezone.utc),
    )

    candidates_b = retriever.retrieve_source_b_identity_adjacent(state)
    candidate_ids = [c.reel_id for c in candidates_b]

    assert "reel_dsa_trees" in candidate_ids
    assert "reel_cloud_k8s" in candidate_ids
    assert "reel_security_auth" in candidate_ids

    dsa_cand = next(c for c in candidates_b if c.reel_id == "reel_dsa_trees")
    assert dsa_cand.graph_distance == 1
    assert dsa_cand.matched_node == "dsa"
    assert dsa_cand.traversal_path == ["software_engineer", "dsa"]


def test_source_c_boundary_exploration_candidates(retriever: MultiSourceRetriever):
    """Test 3: Source C reaches boundary candidates (distributed caching, tree algorithms, k8s)."""
    state = InterestState(
        student_id="student_swe",
        professional_identity={"software_engineer": 0.85},
        domains={},
        goals={},
        depth={},
        content_preference={},
        evidence=[],
        updated_at=datetime.now(timezone.utc),
    )

    candidates_c = retriever.retrieve_source_c_boundary_exploration(state)
    candidate_ids = [c.reel_id for c in candidates_c]

    assert "reel_hld_caching" in candidate_ids
    assert "reel_dsa_trees" in candidate_ids
    assert "reel_cloud_k8s" in candidate_ids

    # Check 2-hop traversal metadata
    caching_cand = next(c for c in candidates_c if c.reel_id == "reel_hld_caching")
    assert caching_cand.source == RetrievalSource.SOURCE_C_BOUNDARY_EXPLORATION
    assert caching_cand.graph_distance == 2
    assert caching_cand.traversal_path == ["software_engineer", "system_design", "distributed_caching"]
    assert caching_cand.matched_node == "distributed_caching"


def test_source_a_topical_retrieves_java_syntax(retriever: MultiSourceRetriever):
    """Test 4: Java topical source retrieves Java syntax candidate."""
    state = InterestState(
        student_id="student_java_fan",
        professional_identity={},
        domains={"java": 0.8},
        goals={},
        depth={},
        content_preference={},
        evidence=[],
        updated_at=datetime.now(timezone.utc),
    )

    candidates_a = retriever.retrieve_source_a_topical(state)
    candidate_ids = [c.reel_id for c in candidates_a]

    assert "reel_java_syntax_basics" in candidate_ids
    java_cand = next(c for c in candidates_a if c.reel_id == "reel_java_syntax_basics")
    assert java_cand.source == RetrievalSource.SOURCE_A_TOPICAL
    assert java_cand.graph_distance == 0
    assert java_cand.traversal_path == ["java"]


def test_gaming_identity_does_not_retrieve_swe_candidates(retriever: MultiSourceRetriever):
    """Test 5: Gaming identity does NOT retrieve SWE HLD/DSA candidates via Source B/C."""
    state = InterestState(
        student_id="student_gamer",
        professional_identity={"gamer": 0.9},
        domains={"gaming": 0.8},
        goals={},
        depth={},
        content_preference={},
        evidence=[],
        updated_at=datetime.now(timezone.utc),
    )

    candidates_b = retriever.retrieve_source_b_identity_adjacent(state)
    candidate_ids_b = [c.reel_id for c in candidates_b]

    assert "reel_hld_caching" not in candidate_ids_b
    assert "reel_dsa_trees" not in candidate_ids_b
    assert "reel_cloud_k8s" not in candidate_ids_b
    assert "reel_security_auth" not in candidate_ids_b


def test_hype_candidate_retrieved_structurally_before_gate(retriever: MultiSourceRetriever):
    """Test 6: Hype candidate (reel_ai_hype_trap) is retrieved structurally if relevant and NOT filtered in retrieval."""
    state = InterestState(
        student_id="student_ai_curious",
        professional_identity={"software_engineer": 0.8},
        domains={"ai": 0.7},
        goals={},
        depth={},
        content_preference={},
        evidence=[],
        updated_at=datetime.now(timezone.utc),
    )

    all_candidates = retriever.retrieve_candidates(state)
    candidate_ids = [c.reel_id for c in all_candidates]

    assert "reel_ai_hype_trap" in candidate_ids, "Hype candidate must be preserved at retrieval stage for later gate evaluation"


def test_multi_source_deduplication_and_provenance(retriever: MultiSourceRetriever):
    """Test 7: Duplicate candidates across multiple sources are represented once with full provenance."""
    state = InterestState(
        student_id="student_swe",
        professional_identity={"software_engineer": 0.9},
        domains={"coding": 0.8, "java": 0.7},
        goals={"career_prep": 0.8},
        depth={},
        content_preference={},
        evidence=[],
        updated_at=datetime.now(timezone.utc),
    )

    candidates = retriever.retrieve_candidates(state)
    reel_ids = [c.reel_id for c in candidates]
    assert len(reel_ids) == len(set(reel_ids)), "Candidates must be strictly deduplicated by reel_id"

    # reel_hld_caching is reached via Source B (1-hop) and Source C (2-hop) and Source A (coding domain)
    hld_cand = next(c for c in candidates if c.reel_id == "reel_hld_caching")
    assert RetrievalSource.SOURCE_B_IDENTITY_ADJACENT in hld_cand.contributing_sources
    assert RetrievalSource.SOURCE_C_BOUNDARY_EXPLORATION in hld_cand.contributing_sources
    assert len(hld_cand.contributing_paths) >= 2


def test_unknown_skill_or_topic_returns_empty(retriever: MultiSourceRetriever):
    """Test 8: Unknown skill or topic returns empty list rather than falling back to unrelated content."""
    state = InterestState(
        student_id="student_unknown",
        professional_identity={"non_existent_identity_123": 0.9},
        domains={"completely_unknown_domain_xyz": 0.8},
        goals={},
        depth={},
        content_preference={},
        evidence=[],
        updated_at=datetime.now(timezone.utc),
    )

    candidates_b = retriever.retrieve_source_b_identity_adjacent(state)
    assert candidates_b == []

    candidates_a = retriever.retrieve_source_a_topical(state)
    assert candidates_a == []


def test_retrieval_metadata_and_determinism(retriever: MultiSourceRetriever):
    """Test 9 & 10: Retrieval contains correct metadata and produces identical ordering on repeated runs."""
    state = InterestState(
        student_id="student_swe",
        professional_identity={"software_engineer": 0.85},
        domains={"java": 0.7, "ai": 0.5},
        goals={"career_prep": 0.9},
        depth={"system_design": DepthLevel.BEGINNER},
        content_preference={},
        evidence=["reel_java_meme", "reel_swe_lifestyle"],
        updated_at=datetime.now(timezone.utc),
    )

    run_1 = retriever.retrieve_candidates(state)
    run_2 = retriever.retrieve_candidates(state)

    assert [c.model_dump() for c in run_1] == [c.model_dump() for c in run_2]
    assert len(run_1) > 0

    for c in run_1:
        assert c.graph_distance is not None
        assert c.graph_distance >= 0
        assert len(c.contributing_sources) >= 1
        assert len(c.contributing_paths) >= 1
