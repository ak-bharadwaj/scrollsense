"""Unit tests for deterministic multi-objective candidate ranking."""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from scrollsense.domain.candidates import Candidate
from scrollsense.domain.enums import DepthLevel, RetrievalSource
from scrollsense.domain.persona import InterestState
from scrollsense.domain.reels import Reel
from scrollsense.gates import CandidateGateEvaluator
from scrollsense.ranking import (
    MultiObjectiveRanker,
    RankingWeights,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUTS_PATH = DATA_DIR / "inputs.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"


@pytest.fixture
def candidate_reels() -> dict[str, Reel]:
    """Fixture providing dictionary of candidate reels."""
    reels: dict[str, Reel] = {}
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for item in json.load(f):
            r = Reel.model_validate(item)
            reels[r.reel_id] = r
    return reels


@pytest.fixture
def ranker(candidate_reels: dict[str, Reel]) -> MultiObjectiveRanker:
    """Fixture providing initialized MultiObjectiveRanker with candidate_repository."""
    return MultiObjectiveRanker(candidate_repository=candidate_reels)


@pytest.fixture
def gate_evaluator() -> CandidateGateEvaluator:
    """Fixture providing initialized CandidateGateEvaluator."""
    return CandidateGateEvaluator()


@pytest.fixture
def swe_trap_state() -> InterestState:
    """Fixture providing persona inferred from canonical SWE trap."""
    return InterestState(
        student_id="student_swe_trap",
        professional_identity={"software_engineer": 0.88, "backend_developer": 0.80},
        domains={"java": 0.80, "coding": 0.75, "backend": 0.75, "hardware": 0.60},
        goals={"career_prep": 0.85},
        depth={"java": DepthLevel.BEGINNER, "coding": DepthLevel.BEGINNER},
        content_preference={"meme": 0.25, "vlog": 0.25},
        evidence=["reel_java_meme", "reel_swe_lifestyle", "reel_interview_joke", "reel_laptop_comparison"],
        updated_at=datetime.now(timezone.utc),
    )


def test_weights_validation_and_boundaries():
    """Test 10: Verify RankingWeights validation enforces sum == 1.0 and unit interval bounds."""
    # Valid default weights pass and sum to 1.0
    default_w = RankingWeights()
    assert (
        default_w.topical_fit
        + default_w.difficulty_match
        + default_w.career_relevance
        + default_w.novelty
        + default_w.quality
        + default_w.hype_penalty
    ) == pytest.approx(1.0)

    # Valid custom weights summing to 1.0 pass
    custom_w = RankingWeights(
        topical_fit=0.30,
        difficulty_match=0.10,
        career_relevance=0.30,
        novelty=0.10,
        quality=0.10,
        hype_penalty=0.10,
    )
    assert custom_w.topical_fit == 0.30

    # Negative individual weight rejected
    with pytest.raises(ValueError):
        RankingWeights(topical_fit=-0.1)

    # Out-of-bounds individual weight > 1.0 rejected
    with pytest.raises(ValueError):
        RankingWeights(career_relevance=1.5)

    # Weights summing to < 1.0 rejected
    with pytest.raises(ValueError) as exc_low:
        RankingWeights(
            topical_fit=0.10,
            difficulty_match=0.10,
            career_relevance=0.10,
            novelty=0.10,
            quality=0.10,
            hype_penalty=0.10,
        )
    assert "Total sum of ranking weights must equal 1.0" in str(exc_low.value)

    # Weights summing to > 1.0 rejected
    with pytest.raises(ValueError) as exc_high:
        RankingWeights(
            topical_fit=0.40,
            difficulty_match=0.40,
            career_relevance=0.40,
            novelty=0.10,
            quality=0.10,
            hype_penalty=0.10,
        )
    assert "Total sum of ranking weights must equal 1.0" in str(exc_high.value)


def test_hld_outranks_literal_java_in_swe_trap(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    candidate_reels: dict[str, Reel],
    swe_trap_state: InterestState,
):
    """Test 1: HLD candidate outranks literal Java syntax candidate when SWE persona is inferred."""
    hld_cand = Candidate(
        reel_id="reel_hld_caching",
        source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT,
        graph_distance=1,
        traversal_path=["software_engineer", "system_design"],
        matched_node="system_design",
        contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT],
        contributing_paths=[["software_engineer", "system_design"]],
    )
    java_cand = Candidate(
        reel_id="reel_java_syntax_basics",
        source=RetrievalSource.SOURCE_A_TOPICAL,
        graph_distance=0,
        traversal_path=["java"],
        matched_node="java",
        contributing_sources=[RetrievalSource.SOURCE_A_TOPICAL],
        contributing_paths=[["java"]],
    )

    candidates = [hld_cand, java_cand]
    gate_results = [gate_evaluator.evaluate(candidate_reels[c.reel_id]) for c in candidates]

    result = ranker.rank_candidates(candidates, swe_trap_state, gate_results)

    assert len(result.ranked_candidates) == 2
    top_candidate = result.ranked_candidates[0]
    assert top_candidate.candidate.reel_id == "reel_hld_caching"
    assert top_candidate.final_score > result.ranked_candidates[1].final_score


def test_core_engineering_candidates_receive_high_career_relevance(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    candidate_reels: dict[str, Reel],
    swe_trap_state: InterestState,
):
    """Test 2: DSA, Cloud, and Cybersecurity candidates receive high career relevance."""
    test_ids = ["reel_dsa_trees", "reel_cloud_k8s", "reel_security_auth"]
    candidates = [
        Candidate(
            reel_id=r_id,
            source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT,
            graph_distance=1,
            traversal_path=["software_engineer", "skill"],
            contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT],
            contributing_paths=[["software_engineer", "skill"]],
        )
        for r_id in test_ids
    ]
    gate_results = [gate_evaluator.evaluate(candidate_reels[c.reel_id]) for c in candidates]

    result = ranker.rank_candidates(candidates, swe_trap_state, gate_results)

    for rc in result.ranked_candidates:
        assert rc.scores.career_relevance >= 0.70
        assert rc.final_score >= 0.60


def test_rejected_hype_candidate_excluded_from_eligible_ranking(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    candidate_reels: dict[str, Reel],
    swe_trap_state: InterestState,
):
    """Test 3: Hype candidate rejected by gate does NOT enter eligible ranking pool."""
    hype_cand = Candidate(
        reel_id="reel_ai_hype_trap",
        source=RetrievalSource.SOURCE_A_TOPICAL,
        graph_distance=0,
        traversal_path=["ai"],
        contributing_sources=[RetrievalSource.SOURCE_A_TOPICAL],
        contributing_paths=[["ai"]],
    )
    substance_cand = Candidate(
        reel_id="reel_ai_substance",
        source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT,
        graph_distance=1,
        traversal_path=["software_engineer", "ai_engineering"],
        contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT],
        contributing_paths=[["software_engineer", "ai_engineering"]],
    )

    candidates = [hype_cand, substance_cand]
    gate_results = [gate_evaluator.evaluate(candidate_reels[c.reel_id]) for c in candidates]

    result = ranker.rank_candidates(candidates, swe_trap_state, gate_results)

    # Only substance candidate is eligible
    eligible_ids = [rc.candidate.reel_id for rc in result.ranked_candidates]
    assert "reel_ai_substance" in eligible_ids
    assert "reel_ai_hype_trap" not in eligible_ids

    # Hype candidate is logged in ineligible_traces
    ineligible_ids = [t.candidate_id for t in result.ineligible_traces]
    assert "reel_ai_hype_trap" in ineligible_ids


def test_difficulty_match_progression(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    swe_trap_state: InterestState,
):
    """Test 4: Difficulty match rewards the next logical step (Intermediate) over Advanced."""
    inter_reel = Reel(
        reel_id="reel_inter",
        title="Intermediate System Design",
        category="System Design",
        depth=DepthLevel.INTERMEDIATE,
        concept_tags=["system_design", "redis"],
    )
    adv_reel = Reel(
        reel_id="reel_adv",
        title="Advanced Distributed Raft Consensus",
        category="System Design",
        depth=DepthLevel.ADVANCED,
        concept_tags=["system_design", "distributed_systems"],
    )

    custom_reels = {"reel_inter": inter_reel, "reel_adv": adv_reel}
    cand_inter = Candidate(reel_id="reel_inter", source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT, graph_distance=1)
    cand_adv = Candidate(reel_id="reel_adv", source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT, graph_distance=1)

    result = ranker.rank_candidates(
        [cand_inter, cand_adv],
        swe_trap_state,
        [gate_evaluator.evaluate(inter_reel), gate_evaluator.evaluate(adv_reel)],
        reels_map=custom_reels,
    )

    inter_ranked = next(r for r in result.ranked_candidates if r.candidate.reel_id == "reel_inter")
    adv_ranked = next(r for r in result.ranked_candidates if r.candidate.reel_id == "reel_adv")

    assert inter_ranked.scores.difficulty_match > adv_ranked.scores.difficulty_match


def test_gaming_candidates_do_not_receive_artificial_swe_career_relevance(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    candidate_reels: dict[str, Reel],
    swe_trap_state: InterestState,
):
    """Test 5: Gaming content receives low career relevance for SWE persona."""
    gaming_cand = Candidate(
        reel_id="reel_gaming_clip",
        source=RetrievalSource.SOURCE_A_TOPICAL,
        graph_distance=0,
        traversal_path=["gaming"],
    )
    # Using candidate_reels or mock gaming reel
    gaming_reel = Reel(
        reel_id="reel_gaming_clip",
        title="1v5 Clutch",
        category="Gaming",
        depth=DepthLevel.BEGINNER,
        concept_tags=["fps_gaming"],
    )
    custom_map = {"reel_gaming_clip": gaming_reel}
    result = ranker.rank_candidates(
        [gaming_cand],
        swe_trap_state,
        [gate_evaluator.evaluate(gaming_reel)],
        reels_map=custom_map,
    )

    assert result.ranked_candidates[0].scores.career_relevance <= 0.10


def test_safety_rejected_candidates_never_appear_as_eligible(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    swe_trap_state: InterestState,
):
    """Test 6: Safety-rejected candidate is never eligible for ranking."""
    unsafe_reel = Reel(
        reel_id="reel_unsafe",
        title="Malware keylogger",
        category="Cybersecurity",
        depth=DepthLevel.BEGINNER,
        concept_tags=["malware"],
    )
    unsafe_cand = Candidate(
        reel_id="reel_unsafe",
        source=RetrievalSource.SOURCE_A_TOPICAL,
    )
    custom_map = {"reel_unsafe": unsafe_reel}
    result = ranker.rank_candidates(
        [unsafe_cand],
        swe_trap_state,
        [gate_evaluator.evaluate(unsafe_reel)],
        reels_map=custom_map,
    )

    assert len(result.ranked_candidates) == 0
    assert len(result.ineligible_traces) == 1
    assert result.ineligible_traces[0].eligible is False


def test_all_objective_scores_bounded_in_unit_interval(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    candidate_reels: dict[str, Reel],
    swe_trap_state: InterestState,
):
    """Test 7: Every objective score and final composite score is bounded in [0.0, 1.0]."""
    candidates = [
        Candidate(reel_id=r_id, source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT, graph_distance=1)
        for r_id in candidate_reels.keys()
    ]
    gate_results = [gate_evaluator.evaluate(candidate_reels[c.reel_id]) for c in candidates]

    result = ranker.rank_candidates(candidates, swe_trap_state, gate_results)

    for rc in result.ranked_candidates:
        assert 0.0 <= rc.scores.topical_fit <= 1.0
        assert 0.0 <= rc.scores.difficulty_match <= 1.0
        assert 0.0 <= rc.scores.career_relevance <= 1.0
        assert 0.0 <= rc.scores.novelty <= 1.0
        assert 0.0 <= rc.scores.quality <= 1.0
        assert 0.0 <= rc.scores.hype_penalty <= 1.0
        assert 0.0 <= rc.final_score <= 1.0


def test_deterministic_repeated_ranking(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    candidate_reels: dict[str, Reel],
    swe_trap_state: InterestState,
):
    """Test 8: Repeated ranking calls with identical inputs produce identical ordering and scores."""
    candidates = [
        Candidate(reel_id=r_id, source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT, graph_distance=1)
        for r_id in candidate_reels.keys()
    ]
    gate_results = [gate_evaluator.evaluate(candidate_reels[c.reel_id]) for c in candidates]

    run_1 = ranker.rank_candidates(candidates, swe_trap_state, gate_results)
    run_2 = ranker.rank_candidates(candidates, swe_trap_state, gate_results)

    assert run_1.model_dump() == run_2.model_dump()


def test_ranking_trace_contains_all_weighted_contributions(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    candidate_reels: dict[str, Reel],
    swe_trap_state: InterestState,
):
    """Test 9: RankingTrace records all 6 weighted contributions explicitly."""
    cand = Candidate(
        reel_id="reel_hld_caching",
        source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT,
        graph_distance=1,
    )
    result = ranker.rank_candidates([cand], swe_trap_state, [gate_evaluator.evaluate(candidate_reels["reel_hld_caching"])])

    trace = result.ranked_candidates[0].trace
    assert "topical_fit" in trace.weighted_contributions
    assert "difficulty_match" in trace.weighted_contributions
    assert "career_relevance" in trace.weighted_contributions
    assert "novelty" in trace.weighted_contributions
    assert "quality" in trace.weighted_contributions
    assert "hype_penalty" in trace.weighted_contributions
    assert trace.eligible is True
