"""Unit tests for deterministic diversity selection and recommendation assembly."""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from scrollsense.domain.candidates import Candidate
from scrollsense.domain.enums import ConfidenceBucket, DepthLevel, RetrievalSource, TechCategory
from scrollsense.domain.gates import GateResult, HypeScore, QualityScore, SafetyResult
from scrollsense.domain.persona import InterestState
from scrollsense.domain.ranking import ObjectiveScores
from scrollsense.domain.reels import Reel
from scrollsense.gates import CandidateGateEvaluator
from scrollsense.ranking import (
    MultiObjectiveRanker,
    RankedCandidate,
    RankingResult,
    RankingTrace,
    RankingWeights,
)
from scrollsense.selection import (
    RecommendationAssembler,
    SelectionPolicy,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUTS_PATH = DATA_DIR / "inputs.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"


@pytest.fixture
def input_reels() -> list[Reel]:
    """Fixture providing input reels list."""
    with open(INPUTS_PATH, "r", encoding="utf-8") as f:
        return [Reel.model_validate(item) for item in json.load(f)]


@pytest.fixture
def candidate_reels_dict() -> dict[str, Reel]:
    """Fixture providing candidate reels by ID."""
    reels: dict[str, Reel] = {}
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for item in json.load(f):
            r = Reel.model_validate(item)
            reels[r.reel_id] = r
    return reels


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


@pytest.fixture
def assembler(candidate_reels_dict: dict[str, Reel]) -> RecommendationAssembler:
    """Fixture providing initialized RecommendationAssembler."""
    return RecommendationAssembler(candidate_repository=candidate_reels_dict)


@pytest.fixture
def ranker(candidate_reels_dict: dict[str, Reel]) -> MultiObjectiveRanker:
    """Fixture providing MultiObjectiveRanker."""
    return MultiObjectiveRanker(candidate_repository=candidate_reels_dict)


@pytest.fixture
def gate_evaluator() -> CandidateGateEvaluator:
    """Fixture providing CandidateGateEvaluator."""
    return CandidateGateEvaluator()


def test_hld_selected_over_repeated_java_and_traceable_current_reel(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    assembler: RecommendationAssembler,
    candidate_reels_dict: dict[str, Reel],
    input_reels: list[Reel],
    swe_trap_state: InterestState,
):
    """Test 1: System Design / HLD candidate is selected as top recommendation and current_reel is formatted."""
    candidates = [
        Candidate(
            reel_id="reel_hld_caching",
            source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT,
            graph_distance=1,
            traversal_path=["software_engineer", "system_design"],
            contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT],
        ),
        Candidate(
            reel_id="reel_java_syntax_basics",
            source=RetrievalSource.SOURCE_A_TOPICAL,
            graph_distance=0,
            traversal_path=["java"],
            contributing_sources=[RetrievalSource.SOURCE_A_TOPICAL],
        ),
    ]

    gate_results = [gate_evaluator.evaluate(candidate_reels_dict[c.reel_id]) for c in candidates]
    ranking_res = ranker.rank_candidates(candidates, swe_trap_state, gate_results)

    trap_inputs = [r for r in input_reels if r.reel_id in swe_trap_state.evidence]
    recs, outputs = assembler.select_and_assemble(ranking_res, swe_trap_state, trap_inputs)

    assert len(recs) == 1
    assert len(outputs) == 1

    selected_output = outputs[0]
    assert selected_output.category == TechCategory.HLD
    assert "Distributed Caching" in selected_output.recommended_tech_reel
    assert selected_output.confidence == ConfidenceBucket.HIGH
    assert selected_output.difficulty == DepthLevel.INTERMEDIATE

    # Verify current_reel contains both reel_id and title
    assert "reel_laptop_comparison" in selected_output.current_reel
    assert " — " in selected_output.current_reel


def test_multiple_candidates_are_diversified(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    candidate_reels_dict: dict[str, Reel],
    input_reels: list[Reel],
    swe_trap_state: InterestState,
):
    """Test 2: When selecting K=3 recommendations, diversity avoids multiple same-category picks."""
    policy = SelectionPolicy(max_recommendations=3, category_diversity_penalty=0.30)
    assembler = RecommendationAssembler(policy=policy, candidate_repository=candidate_reels_dict)

    candidates = [
        Candidate(reel_id="reel_hld_caching", source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT, graph_distance=1, contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT]),
        Candidate(reel_id="reel_dsa_trees", source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT, graph_distance=1, contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT]),
        Candidate(reel_id="reel_cloud_k8s", source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT, graph_distance=1, contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT]),
        Candidate(reel_id="reel_security_auth", source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT, graph_distance=1, contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT]),
    ]
    gate_results = [gate_evaluator.evaluate(candidate_reels_dict[c.reel_id]) for c in candidates]
    ranking_res = ranker.rank_candidates(candidates, swe_trap_state, gate_results)

    recs, outputs = assembler.select_and_assemble(ranking_res, swe_trap_state, input_reels)

    assert len(outputs) == 3
    selected_cats = [o.category for o in outputs]
    assert len(set(selected_cats)) == len(selected_cats)


def test_gaming_history_never_selects_swe_content(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    assembler: RecommendationAssembler,
    candidate_reels_dict: dict[str, Reel],
    input_reels: list[Reel],
):
    """Test 3: Gaming history produces gaming/hardware recommendation, never SWE HLD."""
    gamer_state = InterestState(
        student_id="student_gamer",
        professional_identity={"gamer": 0.90},
        domains={"gaming": 0.90},
        goals={},
        depth={},
        content_preference={"gameplay_clip": 1.0},
        evidence=["reel_gaming_clip"],
        updated_at=datetime.now(timezone.utc),
    )

    candidates = [
        Candidate(reel_id="reel_gaming_gear", source=RetrievalSource.SOURCE_A_TOPICAL, graph_distance=0, contributing_sources=[RetrievalSource.SOURCE_A_TOPICAL]),
    ]
    gate_results = [gate_evaluator.evaluate(candidate_reels_dict["reel_gaming_gear"])]
    ranking_res = ranker.rank_candidates(candidates, gamer_state, gate_results)

    gaming_inputs = [r for r in input_reels if r.reel_id == "reel_gaming_clip"]
    recs, outputs = assembler.select_and_assemble(ranking_res, gamer_state, gaming_inputs)

    assert len(outputs) == 1
    assert outputs[0].category == TechCategory.HARDWARE
    assert "mechanical keyboard" in outputs[0].recommended_tech_reel.lower()


def test_rejected_hype_and_safety_candidates_cannot_be_selected(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    assembler: RecommendationAssembler,
    candidate_reels_dict: dict[str, Reel],
    input_reels: list[Reel],
    swe_trap_state: InterestState,
):
    """Test 4 & 5: Rejected hype and safety candidates never become final recommendations."""
    candidates = [
        Candidate(reel_id="reel_ai_hype_trap", source=RetrievalSource.SOURCE_A_TOPICAL, contributing_sources=[RetrievalSource.SOURCE_A_TOPICAL]),
    ]
    gate_results = [gate_evaluator.evaluate(candidate_reels_dict["reel_ai_hype_trap"])]
    ranking_res = ranker.rank_candidates(candidates, swe_trap_state, gate_results)

    recs, outputs = assembler.select_and_assemble(ranking_res, swe_trap_state, input_reels)
    assert len(recs) == 0
    assert len(outputs) == 0


def test_explanation_references_real_reel_ids_and_graph_path(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    assembler: RecommendationAssembler,
    candidate_reels_dict: dict[str, Reel],
    input_reels: list[Reel],
    swe_trap_state: InterestState,
):
    """Test 6 & 7: Explanations reference real observed reel IDs and real graph paths without fabrication."""
    cand = Candidate(
        reel_id="reel_hld_caching",
        source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT,
        graph_distance=1,
        traversal_path=["software_engineer", "system_design"],
        contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT],
    )
    ranking_res = ranker.rank_candidates([cand], swe_trap_state, [gate_evaluator.evaluate(candidate_reels_dict["reel_hld_caching"])])

    trap_inputs = [r for r in input_reels if r.reel_id in swe_trap_state.evidence]
    recs, outputs = assembler.select_and_assemble(ranking_res, swe_trap_state, trap_inputs)

    out = outputs[0]
    assert "Software Engineer" in out.interest_detected
    assert "reel_java_meme" in out.why
    assert "reel_swe_lifestyle" in out.why
    assert "software_engineer -> system_design" in out.why_this_recommendation
    assert "redis" in out.why_this_recommendation
    assert "cache_invalidation" in out.why_this_recommendation


def test_confidence_ranking_margin_boundaries_and_single_candidate(assembler: RecommendationAssembler):
    """Test 8: Confidence derivation correctly responds to score margins and handles single-candidate case."""
    explainer = assembler.explainer

    def make_ranked_cand(cand_id: str, score: float) -> RankedCandidate:
        cand = Candidate(reel_id=cand_id, source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT)
        scores = ObjectiveScores(
            topical_fit=0.8, difficulty_match=1.0, career_relevance=0.9,
            novelty=0.85, quality=0.85, hype_penalty=0.1, final_score=score
        )
        trace = RankingTrace(
            candidate_id=cand_id, eligible=True, objective_scores=scores,
            weights=RankingWeights(), weighted_contributions={}, final_score=score,
            gate_result=GateResult(
                candidate_id=cand_id, passed=True,
                safety=SafetyResult(passed=True),
                quality=QualityScore(concept_anchor_score=0.9, depth_score=0.7),
                hype=HypeScore(pattern_penalty=0.1, promotional_language_score=0.1)
            )
        )
        return RankedCandidate(candidate=cand, scores=scores, final_score=score, trace=trace)

    high_state = InterestState(
        student_id="s1", professional_identity={"software_engineer": 0.85},
        domains={"coding": 0.8}, goals={}, depth={}, content_preference={},
        evidence=["r1", "r2", "r3"], updated_at=datetime.now(timezone.utc)
    )

    top_cand = make_ranked_cand("c1", 0.75)
    distant_runner_up = make_ranked_cand("c2", 0.60)   # margin = 0.15 >= 0.06 -> HIGH
    tight_runner_up = make_ranked_cand("c3", 0.73)     # margin = 0.02 < 0.06 -> MEDIUM

    # 1. Distant runner-up yields High confidence
    assert explainer.derive_confidence(high_state, top_cand, runner_up_candidate=distant_runner_up) == ConfidenceBucket.HIGH

    # 2. Tight margin degrades to Medium confidence
    assert explainer.derive_confidence(high_state, top_cand, runner_up_candidate=tight_runner_up) == ConfidenceBucket.MEDIUM

    # 3. Single-candidate case (runner_up=None) yields deterministic High confidence under high evidence
    assert explainer.derive_confidence(high_state, top_cand, runner_up_candidate=None) == ConfidenceBucket.HIGH


def test_deterministic_repeated_selection(
    ranker: MultiObjectiveRanker,
    gate_evaluator: CandidateGateEvaluator,
    assembler: RecommendationAssembler,
    candidate_reels_dict: dict[str, Reel],
    input_reels: list[Reel],
    swe_trap_state: InterestState,
):
    """Test 9: Repeated recommendation selection and assembly produces byte-for-byte identical output."""
    candidates = [
        Candidate(reel_id="reel_hld_caching", source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT, graph_distance=1, contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT]),
        Candidate(reel_id="reel_dsa_trees", source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT, graph_distance=1, contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT]),
    ]
    gate_results = [gate_evaluator.evaluate(candidate_reels_dict[c.reel_id]) for c in candidates]
    ranking_res = ranker.rank_candidates(candidates, swe_trap_state, gate_results)

    recs_1, outputs_1 = assembler.select_and_assemble(ranking_res, swe_trap_state, input_reels)
    recs_2, outputs_2 = assembler.select_and_assemble(ranking_res, swe_trap_state, input_reels)

    assert [r.model_dump() for r in recs_1] == [r.model_dump() for r in recs_2]
    assert [o.model_dump() for o in outputs_1] == [o.model_dump() for o in outputs_2]


def test_runner_up_margin_selection_for_k3(candidate_reels_dict: dict[str, Reel], input_reels: list[Reel]):
    """Test 10: Verify K=3 recommendations correctly compare each candidate against its strictly next lower-ranked runner-up."""
    policy = SelectionPolicy(max_recommendations=3, category_diversity_penalty=0.0)
    assembler = RecommendationAssembler(policy=policy, candidate_repository=candidate_reels_dict)

    high_state = InterestState(
        student_id="s_k3",
        professional_identity={"software_engineer": 0.88},
        domains={"coding": 0.8},
        goals={"career_prep": 0.8},
        depth={},
        content_preference={},
        evidence=["reel_java_meme", "reel_swe_lifestyle", "reel_interview_joke"],
        updated_at=datetime.now(timezone.utc),
    )

    def make_ranked(cand_id: str, score: float) -> RankedCandidate:
        c = Candidate(reel_id=cand_id, source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT)
        obj_scores = ObjectiveScores(
            topical_fit=0.8, difficulty_match=1.0, career_relevance=0.9,
            novelty=0.8, quality=0.8, hype_penalty=0.1, final_score=score,
        )
        trace = RankingTrace(
            candidate_id=cand_id, eligible=True, objective_scores=obj_scores,
            weights=RankingWeights(), weighted_contributions={}, final_score=score,
            gate_result=GateResult(
                candidate_id=cand_id, passed=True, safety=SafetyResult(passed=True),
                quality=QualityScore(concept_anchor_score=0.9, depth_score=0.7),
                hype=HypeScore(pattern_penalty=0.1, promotional_language_score=0.1),
            ),
        )
        return RankedCandidate(candidate=c, scores=obj_scores, final_score=score, trace=trace)

    # 3 ranked candidates with scores: 0.90, 0.84, 0.80
    rc1 = make_ranked("reel_hld_caching", 0.90)     # runner-up is rc2 (0.84), margin = 0.06 >= 0.06 -> HIGH
    rc2 = make_ranked("reel_dsa_trees", 0.84)       # runner-up is rc3 (0.80), margin = 0.04 < 0.06 -> MEDIUM
    rc3 = make_ranked("reel_cloud_k8s", 0.80)       # no runner-up -> default margin 0.15 >= 0.06 -> HIGH

    ranking_res = RankingResult(ranked_candidates=[rc1, rc2, rc3])

    recs, outputs = assembler.select_and_assemble(ranking_res, high_state, input_reels)

    assert len(outputs) == 3
    assert outputs[0].confidence == ConfidenceBucket.HIGH
    assert outputs[1].confidence == ConfidenceBucket.MEDIUM
    assert outputs[2].confidence == ConfidenceBucket.HIGH
