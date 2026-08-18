"""Unit tests for ScrollSense v4 domain contracts."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from scrollsense.domain import (
    Candidate,
    ConfidenceBucket,
    DepthLevel,
    FeedbackEvent,
    FeedbackOutcome,
    GraphEdge,
    GraphNode,
    HypeScore,
    IdentitySkillGraph,
    InterestEvidence,
    InterestState,
    NodeType,
    ObjectiveScores,
    QualityScore,
    Recommendation,
    Reel,
    ReelSignal,
    RelationType,
    RetrievalSource,
    SafetyResult,
)


def test_reel_valid():
    """Verify valid Reel creation."""
    reel = Reel(
        reel_id="reel_1",
        title="10-minute System Design Crash Course",
        category="system_design",
        format="tutorial",
        tone="technical",
        depth=DepthLevel.INTERMEDIATE,
        concept_tags=["distributed_systems", "caching"],
        transcript="Today we look at cache invalidation...",
    )
    assert reel.reel_id == "reel_1"
    assert reel.depth == DepthLevel.INTERMEDIATE
    assert len(reel.concept_tags) == 2


def test_reel_invalid():
    """Verify Reel validation errors on empty required fields and invalid types."""
    with pytest.raises(ValidationError):
        Reel(reel_id="", title="Title", category="cat")  # empty reel_id

    with pytest.raises(ValidationError):
        Reel(reel_id="r1", title="", category="cat")  # empty title


def test_interest_evidence_validation():
    """Verify InterestEvidence validation and optional weight bounds."""
    evidence = InterestEvidence(
        evidence_type=RelationType.CAREER_STAGE_SIGNAL,
        value="candidate",
        weight=0.85,
    )
    assert evidence.weight == 0.85

    # Out-of-bounds weight
    with pytest.raises(ValidationError):
        InterestEvidence(evidence_type="test", value="val", weight=1.5)

    with pytest.raises(ValidationError):
        InterestEvidence(evidence_type="test", value="val", weight=-0.1)


def test_reel_signal_validation():
    """Verify ReelSignal construction and validation."""
    now = datetime.now(timezone.utc)
    evidence = [InterestEvidence(evidence_type="career_stage_signal", value="candidate")]
    signal = ReelSignal(
        reel_id="reel_123",
        signal_version="v1",
        ontology_version="v1",
        model_version="gemini-3.7-flash",
        generated_at=now,
        topic="interview_jokes",
        format="meme",
        tone="humorous",
        depth=DepthLevel.BEGINNER,
        concept_tags=["career_preparation"],
        interest_evidence=evidence,
    )
    assert signal.topic == "interview_jokes"
    assert len(signal.interest_evidence) == 1

    # Missing required field
    with pytest.raises(ValidationError):
        ReelSignal(
            reel_id="r1",
            signal_version="v1",
            ontology_version="v1",
            model_version="v1",
            generated_at=now,
            topic="test",
            format="test",
            tone="test",
            # missing depth
        )


def test_graph_models_validation():
    """Verify GraphNode, GraphEdge, and IdentitySkillGraph."""
    node1 = GraphNode(id="software_engineer", category=NodeType.PROFESSIONAL_IDENTITY)
    node2 = GraphNode(id="system_design", category=NodeType.SKILL, label="System Design")

    edge = GraphEdge(
        from_node="software_engineer",
        to_node="system_design",
        relation_type=RelationType.IDENTITY_ADJACENT_SKILL,
        weight=0.8,
    )

    graph = IdentitySkillGraph(version="v1.0", nodes=[node1, node2], edges=[edge])
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.edges[0].weight == 0.8

    # Edge with invalid weight
    with pytest.raises(ValidationError):
        GraphEdge(
            from_node="n1",
            to_node="n2",
            relation_type="rel",
            weight=1.2,
        )


def test_interest_state_validation():
    """Verify InterestState construction and validation."""
    now = datetime.now(timezone.utc)
    state = InterestState(
        student_id="student_42",
        professional_identity={"software_engineer": 0.86},
        domains={"backend": 0.7, "ai": 0.3},
        goals={"career_prep": 0.8},
        depth={"backend": DepthLevel.INTERMEDIATE},
        content_preference={"humor": 0.6, "tutorial": 0.7},
        evidence=["reel_1", "reel_2"],
        updated_at=now,
    )
    assert state.professional_identity["software_engineer"] == 0.86
    assert state.depth["backend"] == DepthLevel.INTERMEDIATE

    # Missing updated_at or student_id
    with pytest.raises(ValidationError):
        InterestState(student_id="", updated_at=now)


def test_candidate_validation():
    """Verify Candidate construction with metadata and path."""
    cand = Candidate(
        reel_id="reel_sys_1",
        source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT,
        matched_node="system_design",
        graph_distance=1,
        traversal_path=["software_engineer", "system_design"],
        initial_score=0.75,
    )
    assert cand.source == RetrievalSource.SOURCE_B_IDENTITY_ADJACENT
    assert cand.graph_distance == 1
    assert len(cand.traversal_path) == 2

    # Negative graph distance should fail
    with pytest.raises(ValidationError):
        Candidate(
            reel_id="r1",
            source=RetrievalSource.SOURCE_A_TOPICAL,
            graph_distance=-1,
        )


def test_gates_validation():
    """Verify SafetyResult, QualityScore, and HypeScore validation."""
    safety_pass = SafetyResult(passed=True)
    safety_fail = SafetyResult(passed=False, reason="Prohibited policy violation")
    assert safety_pass.passed is True
    assert safety_fail.reason == "Prohibited policy violation"

    quality = QualityScore(concept_anchor_score=0.85, depth_score=0.7)
    assert quality.concept_anchor_score == 0.85

    hype = HypeScore(pattern_penalty=0.2, promotional_language_score=0.1)
    assert hype.pattern_penalty == 0.2

    # Quality score out of bounds
    with pytest.raises(ValidationError):
        QualityScore(concept_anchor_score=1.5, depth_score=0.5)

    # Hype score out of bounds
    with pytest.raises(ValidationError):
        HypeScore(pattern_penalty=-0.1, promotional_language_score=0.5)


def test_ranking_and_recommendation_validation():
    """Verify ObjectiveScores and Recommendation schemas."""
    scores = ObjectiveScores(
        topical_fit=0.8,
        difficulty_match=0.9,
        career_relevance=0.85,
        novelty=0.4,
        quality=0.88,
        hype_penalty=0.1,
        final_score=0.78,
    )
    assert scores.final_score == 0.78

    rec = Recommendation(
        reel_id="reel_hld_01",
        title="High-Level Architecture for Beginners",
        final_score=0.82,
        confidence=ConfidenceBucket.HIGH,
        retrieval_source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT,
        traversal_path=["software_engineer", "system_design"],
        objective_scores=scores,
        explanation="Inferred SWE identity with career prep goal matches System Design adjacency.",
        evidence_reel_ids=["reel_joke_1", "reel_vlog_2", "reel_laptop_3"],
    )
    assert rec.confidence == ConfidenceBucket.HIGH
    assert len(rec.evidence_reel_ids) == 3


def test_feedback_event_validation():
    """Verify FeedbackEvent construction and valid outcomes."""
    now = datetime.now(timezone.utc)
    event = FeedbackEvent(
        recommendation_id="rec_100",
        student_id="student_42",
        outcome=FeedbackOutcome.ACCEPTED,
        observed_at=now,
    )
    assert event.outcome == FeedbackOutcome.ACCEPTED

    # Invalid outcome value
    with pytest.raises(ValidationError):
        FeedbackEvent(
            recommendation_id="rec_100",
            student_id="student_42",
            outcome="invalid_outcome",  # type: ignore[arg-type]
            observed_at=now,
        )


def test_forbid_extra_fields():
    """Verify that models reject unpermitted extra fields."""
    with pytest.raises(ValidationError):
        SafetyResult(passed=True, unexpected_field="foo")  # type: ignore[call-arg]
