"""Unit tests for hardened ScrollSense v4 domain contracts."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from scrollsense.domain import (
    Candidate,
    ConfidenceBucket,
    DepthLevel,
    EvidenceType,
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
    RecommendationOutput,
    Reel,
    ReelSignal,
    RelationType,
    RetrievalSource,
    SafetyResult,
    TechCategory,
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
        Reel(reel_id="", title="Title", category="cat")

    with pytest.raises(ValidationError):
        Reel(reel_id="r1", title="", category="cat")


def test_interest_evidence_validation():
    """Verify InterestEvidence requires typed EvidenceType and valid weights in [0, 1]."""
    evidence = InterestEvidence(
        evidence_type=EvidenceType.CAREER_STAGE_SIGNAL,
        value="candidate",
        weight=0.85,
    )
    assert evidence.evidence_type == EvidenceType.CAREER_STAGE_SIGNAL
    assert evidence.weight == 0.85

    # Boundary weights
    ev_zero = InterestEvidence(evidence_type=EvidenceType.DOMAIN_SIGNAL, value="backend", weight=0.0)
    ev_one = InterestEvidence(evidence_type=EvidenceType.DOMAIN_SIGNAL, value="backend", weight=1.0)
    assert ev_zero.weight == 0.0
    assert ev_one.weight == 1.0

    # Invalid evidence_type (raw unmapped string)
    with pytest.raises(ValidationError):
        InterestEvidence(evidence_type="invalid_type", value="val")  # type: ignore[arg-type]

    # Out-of-bounds weights
    with pytest.raises(ValidationError):
        InterestEvidence(evidence_type=EvidenceType.GOAL_SIGNAL, value="val", weight=1.001)

    with pytest.raises(ValidationError):
        InterestEvidence(evidence_type=EvidenceType.GOAL_SIGNAL, value="val", weight=-0.001)


def test_reel_signal_validation():
    """Verify ReelSignal construction and validation."""
    now = datetime.now(timezone.utc)
    evidence = [InterestEvidence(evidence_type=EvidenceType.CAREER_STAGE_SIGNAL, value="candidate")]
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
    """Verify GraphNode, GraphEdge with RelationType enum, and IdentitySkillGraph."""
    node1 = GraphNode(id="software_engineer", category=NodeType.PROFESSIONAL_IDENTITY)
    node2 = GraphNode(id="system_design", category=NodeType.SKILL, label="System Design")

    edge = GraphEdge(
        from_node="software_engineer",
        to_node="system_design",
        relation_type=RelationType.IDENTITY_ADJACENT_SKILL,
        weight=0.8,
    )
    assert edge.relation_type == RelationType.IDENTITY_ADJACENT_SKILL

    graph = IdentitySkillGraph(version="v1.0", nodes=[node1, node2], edges=[edge])
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1

    # Invalid relation_type
    with pytest.raises(ValidationError):
        GraphEdge(
            from_node="n1",
            to_node="n2",
            relation_type="arbitrary_untyped_relation",  # type: ignore[arg-type]
            weight=0.5,
        )

    # Invalid node category
    with pytest.raises(ValidationError):
        GraphNode(id="n1", category="invalid_category")  # type: ignore[arg-type]

    # Out-of-bounds edge weights
    with pytest.raises(ValidationError):
        GraphEdge(
            from_node="n1",
            to_node="n2",
            relation_type=RelationType.TOPIC_IMPLIES_IDENTITY,
            weight=1.01,
        )

    with pytest.raises(ValidationError):
        GraphEdge(
            from_node="n1",
            to_node="n2",
            relation_type=RelationType.TOPIC_IMPLIES_IDENTITY,
            weight=-0.01,
        )


def test_interest_state_weights_constrained():
    """Verify InterestState strictly validates all weights in [0, 1]."""
    now = datetime.now(timezone.utc)
    state = InterestState(
        student_id="student_42",
        professional_identity={"software_engineer": 0.86, "ml_engineer": 0.0},
        domains={"backend": 0.7, "ai": 1.0},
        goals={"career_prep": 0.8},
        depth={"backend": DepthLevel.INTERMEDIATE},
        content_preference={"humor": 0.6, "tutorial": 0.0},
        evidence=["reel_1", "reel_2"],
        updated_at=now,
    )
    assert state.professional_identity["software_engineer"] == 0.86
    assert state.domains["ai"] == 1.0

    # Weight > 1.0 in professional_identity
    with pytest.raises(ValidationError) as exc:
        InterestState(
            student_id="s1",
            professional_identity={"software_engineer": 1.05},
            updated_at=now,
        )
    assert "must be in [0.0, 1.0]" in str(exc.value)

    # Weight < 0.0 in domains
    with pytest.raises(ValidationError) as exc:
        InterestState(
            student_id="s1",
            domains={"backend": -0.1},
            updated_at=now,
        )
    assert "must be in [0.0, 1.0]" in str(exc.value)

    # Weight > 1.0 in goals
    with pytest.raises(ValidationError) as exc:
        InterestState(
            student_id="s1",
            goals={"career_prep": 2.0},
            updated_at=now,
        )
    assert "must be in [0.0, 1.0]" in str(exc.value)

    # Weight < 0.0 in content_preference
    with pytest.raises(ValidationError) as exc:
        InterestState(
            student_id="s1",
            content_preference={"tutorial": -0.5},
            updated_at=now,
        )
    assert "must be in [0.0, 1.0]" in str(exc.value)


def test_candidate_validation():
    """Verify Candidate construction with typed source and path."""
    cand = Candidate(
        reel_id="reel_sys_1",
        source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT,
        matched_node="system_design",
        graph_distance=1,
        traversal_path=["software_engineer", "system_design"],
        initial_score=0.75,
    )
    assert cand.source == RetrievalSource.SOURCE_B_IDENTITY_ADJACENT

    # Invalid source enum
    with pytest.raises(ValidationError):
        Candidate(
            reel_id="r1",
            source="Random Source",  # type: ignore[arg-type]
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

    # Scores out of [0, 1] bounds
    with pytest.raises(ValidationError):
        QualityScore(concept_anchor_score=1.5, depth_score=0.5)

    with pytest.raises(ValidationError):
        QualityScore(concept_anchor_score=0.5, depth_score=-0.1)

    with pytest.raises(ValidationError):
        HypeScore(pattern_penalty=-0.1, promotional_language_score=0.5)

    with pytest.raises(ValidationError):
        HypeScore(pattern_penalty=0.5, promotional_language_score=1.2)


def test_objective_scores_bounded():
    """Verify all ObjectiveScores fields are strictly constrained to [0, 1]."""
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

    # Test each field failing when > 1.0 or < 0.0
    with pytest.raises(ValidationError):
        ObjectiveScores(
            topical_fit=1.1,
            difficulty_match=0.5,
            career_relevance=0.5,
            novelty=0.5,
            quality=0.5,
            hype_penalty=0.5,
        )

    with pytest.raises(ValidationError):
        ObjectiveScores(
            topical_fit=0.5,
            difficulty_match=-0.1,
            career_relevance=0.5,
            novelty=0.5,
            quality=0.5,
            hype_penalty=0.5,
        )

    with pytest.raises(ValidationError):
        ObjectiveScores(
            topical_fit=0.5,
            difficulty_match=0.5,
            career_relevance=1.5,
            novelty=0.5,
            quality=0.5,
            hype_penalty=0.5,
        )

    with pytest.raises(ValidationError):
        ObjectiveScores(
            topical_fit=0.5,
            difficulty_match=0.5,
            career_relevance=0.5,
            novelty=-0.2,
            quality=0.5,
            hype_penalty=0.5,
        )

    with pytest.raises(ValidationError):
        ObjectiveScores(
            topical_fit=0.5,
            difficulty_match=0.5,
            career_relevance=0.5,
            novelty=0.5,
            quality=1.01,
            hype_penalty=0.5,
        )

    with pytest.raises(ValidationError):
        ObjectiveScores(
            topical_fit=0.5,
            difficulty_match=0.5,
            career_relevance=0.5,
            novelty=0.5,
            quality=0.5,
            hype_penalty=-0.05,
        )

    with pytest.raises(ValidationError):
        ObjectiveScores(
            topical_fit=0.5,
            difficulty_match=0.5,
            career_relevance=0.5,
            novelty=0.5,
            quality=0.5,
            hype_penalty=0.5,
            final_score=1.5,
        )


def test_recommendation_strictly_typed():
    """Verify Recommendation requires typed RetrievalSource and ConfidenceBucket."""
    scores = ObjectiveScores(
        topical_fit=0.8,
        difficulty_match=0.9,
        career_relevance=0.85,
        novelty=0.4,
        quality=0.88,
        hype_penalty=0.1,
        final_score=0.78,
    )

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
    assert rec.retrieval_source == RetrievalSource.SOURCE_B_IDENTITY_ADJACENT

    # Invalid retrieval_source string
    with pytest.raises(ValidationError):
        Recommendation(
            reel_id="r1",
            title="t",
            final_score=0.8,
            confidence=ConfidenceBucket.LOW,
            retrieval_source="raw_string_source",  # type: ignore[arg-type]
            explanation="exp",
        )

    # Invalid confidence bucket
    with pytest.raises(ValidationError):
        Recommendation(
            reel_id="r1",
            title="t",
            final_score=0.8,
            confidence="CalibratedHigh",  # type: ignore[arg-type]
            retrieval_source=RetrievalSource.SOURCE_A_TOPICAL,
            explanation="exp",
        )

    # Final score out of [0, 1]
    with pytest.raises(ValidationError):
        Recommendation(
            reel_id="r1",
            title="t",
            final_score=1.2,
            confidence=ConfidenceBucket.MEDIUM,
            retrieval_source=RetrievalSource.SOURCE_A_TOPICAL,
            explanation="exp",
        )


def test_recommendation_output_valid():
    """Verify valid RecommendationOutput construction across required problem categories."""
    output = RecommendationOutput(
        current_reel="Java meme about NullPointerException",
        interest_detected="Software Engineering (Backend Developer)",
        why="User engaged with Java error-handling and developer workplace humor",
        recommended_tech_reel="Distributed Caching with Redis Explained",
        category=TechCategory.HLD,
        why_this_recommendation="Broadens Java fundamentals toward backend system design without getting stuck in syntax repetition",
        difficulty=DepthLevel.BEGINNER,
        confidence=ConfidenceBucket.HIGH,
    )
    assert output.category == TechCategory.HLD
    assert output.difficulty == DepthLevel.BEGINNER
    assert output.confidence == ConfidenceBucket.HIGH


@pytest.mark.parametrize(
    "category",
    [
        TechCategory.AI,
        TechCategory.DSA,
        TechCategory.JAVA,
        TechCategory.HLD,
        TechCategory.CYBERSECURITY,
        TechCategory.CLOUD,
        TechCategory.HARDWARE,
        TechCategory.CAREER,
        TechCategory.OTHER,
    ],
)
def test_recommendation_output_all_categories(category: TechCategory):
    """Verify RecommendationOutput supports all 9 defined TechCategory values."""
    output = RecommendationOutput(
        current_reel="reel_001",
        interest_detected="Tech Enthusiast",
        why="Watched technical overview",
        recommended_tech_reel="Intro to " + category.value,
        category=category,
        why_this_recommendation="Targeted technical progression",
        difficulty=DepthLevel.INTERMEDIATE,
        confidence=ConfidenceBucket.MEDIUM,
    )
    assert output.category == category


def test_recommendation_output_invalid():
    """Verify RecommendationOutput validation failures for invalid category, difficulty, confidence, and missing fields."""
    valid_args = {
        "current_reel": "reel_01",
        "interest_detected": "SWE",
        "why": "Watched developer vlog",
        "recommended_tech_reel": "System Design Basics",
        "category": TechCategory.HLD,
        "why_this_recommendation": "Matches inferred identity",
        "difficulty": DepthLevel.BEGINNER,
        "confidence": ConfidenceBucket.HIGH,
    }

    # Empty string fields
    for field in ["current_reel", "interest_detected", "why", "recommended_tech_reel", "why_this_recommendation"]:
        invalid_args = dict(valid_args)
        invalid_args[field] = ""
        with pytest.raises(ValidationError):
            RecommendationOutput(**invalid_args)

    # Invalid category
    invalid_cat = dict(valid_args)
    invalid_cat["category"] = "DevOps"  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        RecommendationOutput(**invalid_cat)

    # Invalid difficulty
    invalid_diff = dict(valid_args)
    invalid_diff["difficulty"] = "Hard"  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        RecommendationOutput(**invalid_diff)

    # Invalid confidence
    invalid_conf = dict(valid_args)
    invalid_conf["confidence"] = "VeryHigh"  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        RecommendationOutput(**invalid_conf)


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

    with pytest.raises(ValidationError):
        RecommendationOutput(  # type: ignore[call-arg]
            current_reel="reel_01",
            interest_detected="SWE",
            why="reason",
            recommended_tech_reel="rec",
            category=TechCategory.AI,
            why_this_recommendation="why",
            difficulty=DepthLevel.BEGINNER,
            confidence=ConfidenceBucket.HIGH,
            extra_field="unsupported",
        )
