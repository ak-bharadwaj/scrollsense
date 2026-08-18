"""Integration tests for the full end-to-end ScrollSense recommendation engine."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel
import pytest

from scrollsense.domain.enums import ConfidenceBucket, DepthLevel, TechCategory
from scrollsense.domain.recommendation import RecommendationOutput
from scrollsense.domain.reels import Reel
from scrollsense.engine import EngineResult, NoEligibleCandidatesError, ScrollSenseEngine
from scrollsense.graph.loader import GraphLoader
from scrollsense.graph.store import GraphStore
from scrollsense.retrieval.repository import CandidateRepository
from scrollsense.signals.llm_extractor import LLMStructuredSignalExtractor

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GRAPH_PATH = DATA_DIR / "identity_skill_graph.json"
INPUTS_PATH = DATA_DIR / "inputs.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"


@pytest.fixture
def graph_store() -> GraphStore:
    """Fixture providing initialized GraphStore."""
    return GraphLoader.load_from_json(GRAPH_PATH)


@pytest.fixture
def candidate_repo() -> CandidateRepository:
    """Fixture providing CandidateRepository."""
    return CandidateRepository.load_from_json(CANDIDATES_PATH)


@pytest.fixture
def all_input_reels() -> dict[str, Reel]:
    """Fixture providing input reels by reel_id."""
    reels: dict[str, Reel] = {}
    with open(INPUTS_PATH, "r", encoding="utf-8") as f:
        for item in json.load(f):
            r = Reel.model_validate(item)
            reels[r.reel_id] = r
    return reels


@pytest.fixture
def default_engine(graph_store: GraphStore, candidate_repo: CandidateRepository) -> ScrollSenseEngine:
    """Fixture providing default deterministic ScrollSenseEngine."""
    return ScrollSenseEngine.create_default(
        graph_store=graph_store,
        candidate_repo=candidate_repo,
    )


class MockLLMProvider:
    """Mock LLM provider for deterministic end-to-end integration testing."""

    def __init__(self, responses: dict[str, Any], model_name: str = "gemini-3.5-flash") -> None:
        self._responses = responses
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_structured_json(self, prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
        for reel_id, response in self._responses.items():
            if f"- Reel ID: {reel_id}" in prompt:
                return response
        raise RuntimeError(f"No mock response configured for prompt: {prompt[:100]}...")


@pytest.fixture
def mock_trap_provider() -> MockLLMProvider:
    trap_responses = {
        "reel_java_meme": {
            "topic": "java_meme",
            "format": "meme",
            "tone": "humorous",
            "depth": "Beginner",
            "concept_tags": ["java", "exception_handling", "production_debugging"],
            "interest_evidence": [
                {"evidence_type": "topic_implies_identity", "value": "software_engineer", "weight": 0.65},
                {"evidence_type": "domain_signal", "value": "java", "weight": 0.80},
                {"evidence_type": "domain_signal", "value": "backend", "weight": 0.60},
            ],
        },
        "reel_swe_lifestyle": {
            "topic": "swe_lifestyle",
            "format": "vlog",
            "tone": "casual",
            "depth": "Beginner",
            "concept_tags": ["software_engineering", "workplace_culture"],
            "interest_evidence": [
                {"evidence_type": "topic_implies_identity", "value": "software_engineer", "weight": 0.85},
                {"evidence_type": "professional_identity_signal", "value": "backend_developer", "weight": 0.80},
                {"evidence_type": "domain_signal", "value": "backend", "weight": 0.75},
            ],
        },
        "reel_interview_joke": {
            "topic": "interview_joke",
            "format": "interview_joke",
            "tone": "humorous",
            "depth": "Beginner",
            "concept_tags": ["coding_interviews", "dsa", "career_prep"],
            "interest_evidence": [
                {"evidence_type": "career_stage_signal", "value": "candidate", "weight": 0.80},
                {"evidence_type": "goal_signal", "value": "career_prep", "weight": 0.85},
                {"evidence_type": "topic_implies_identity", "value": "software_engineer", "weight": 0.70},
            ],
        },
        "reel_laptop_comparison": {
            "topic": "laptop_comparison",
            "format": "hardware_comparison",
            "tone": "technical",
            "depth": "Intermediate",
            "concept_tags": ["hardware", "developer_workstation", "docker", "local_development"],
            "interest_evidence": [
                {"evidence_type": "professional_identity_signal", "value": "software_engineer", "weight": 0.70},
                {"evidence_type": "domain_signal", "value": "hardware", "weight": 0.60},
                {"evidence_type": "domain_signal", "value": "cloud_infrastructure", "weight": 0.50},
            ],
        },
    }
    return MockLLMProvider(trap_responses)


def test_canonical_swe_trap_end_to_end(
    default_engine: ScrollSenseEngine,
    all_input_reels: dict[str, Reel],
):
    """Test 1: Canonical SWE trap end-to-end integration produces HLD recommendation."""
    trap_inputs = [
        all_input_reels["reel_java_meme"],
        all_input_reels["reel_swe_lifestyle"],
        all_input_reels["reel_interview_joke"],
        all_input_reels["reel_laptop_comparison"],
    ]

    output = default_engine.recommend(
        student_id="student_swe_trap",
        input_reels=trap_inputs,
    )

    assert isinstance(output, RecommendationOutput)
    assert output.category == TechCategory.AI
    assert "Attention Mechanism" in output.recommended_tech_reel
    assert output.interest_detected == "Software Engineer"
    assert output.difficulty == DepthLevel.INTERMEDIATE
    assert "reel_laptop_comparison" in output.current_reel
    assert "transformers" in output.why_this_recommendation
    assert "reel_java_meme" in output.why


def test_mock_llm_extractor_end_to_end(
    graph_store: GraphStore,
    candidate_repo: CandidateRepository,
    all_input_reels: dict[str, Reel],
    mock_trap_provider: MockLLMProvider,
):
    """Test 2: LLMStructuredSignalExtractor with mock provider integrates seamlessly into engine."""
    llm_extractor = LLMStructuredSignalExtractor(
        provider=mock_trap_provider,
        graph=graph_store,
    )

    engine = ScrollSenseEngine.create_default(
        graph_store=graph_store,
        candidate_repo=candidate_repo,
        extractor=llm_extractor,
    )

    trap_inputs = [
        all_input_reels["reel_java_meme"],
        all_input_reels["reel_swe_lifestyle"],
        all_input_reels["reel_interview_joke"],
        all_input_reels["reel_laptop_comparison"],
    ]

    result = engine.recommend_full(
        student_id="student_swe_trap_llm",
        input_reels=trap_inputs,
    )

    assert isinstance(result, EngineResult)
    assert len(result.extracted_signals) == 4
    assert result.interest_state.professional_identity["software_engineer"] > 0.80
    assert result.outputs[0].category == TechCategory.AI
    assert "Attention Mechanism" in result.outputs[0].recommended_tech_reel


def test_gaming_non_trap_end_to_end(
    default_engine: ScrollSenseEngine,
    all_input_reels: dict[str, Reel],
):
    """Test 3: Gaming clip history recommends hardware/gear and never recommends SWE HLD."""
    gaming_inputs = [all_input_reels["reel_gaming_clip"]]

    output = default_engine.recommend(
        student_id="student_gamer",
        input_reels=gaming_inputs,
    )

    assert output.category == TechCategory.HARDWARE
    assert "mechanical keyboard" in output.recommended_tech_reel.lower()
    assert "system design" not in output.why_this_recommendation.lower()


def test_hype_rejection_end_to_end(
    default_engine: ScrollSenseEngine,
    all_input_reels: dict[str, Reel],
):
    """Test 4: Hype candidates retrieved via topical AI search are rejected at the gate and never recommended."""
    ai_inputs = [
        all_input_reels["reel_ai_prompt_hacks"],
    ]

    result = default_engine.recommend_full(
        student_id="student_ai",
        input_reels=ai_inputs,
    )

    # reel_ai_hype_trap must be in ineligible_traces, not outputs
    output_titles = [o.recommended_tech_reel for o in result.outputs]
    assert not any("10 AI Tools That Will Replace" in t for t in output_titles)
    ineligible_ids = [t.candidate_id for t in result.ranking_result.ineligible_traces]
    assert "reel_ai_hype_trap" in ineligible_ids


def test_empty_input_history_raises_value_error(default_engine: ScrollSenseEngine):
    """Test 5: Empty input reel sequence raises ValueError."""
    with pytest.raises(ValueError) as exc:
        default_engine.recommend(student_id="student_empty", input_reels=[])
    assert "input_reels sequence cannot be empty" in str(exc.value)


def test_no_eligible_candidates_raises_no_eligible_candidates_error(
    graph_store: GraphStore,
    all_input_reels: dict[str, Reel],
):
    """Test 6: When candidate repository has no eligible surviving candidates, NoEligibleCandidatesError is raised."""
    empty_repo = CandidateRepository(candidates=[])

    engine = ScrollSenseEngine.create_default(
        graph_store=graph_store,
        candidate_repo=empty_repo,
    )

    with pytest.raises(NoEligibleCandidatesError) as exc:
        engine.recommend(
            student_id="student_empty_repo",
            input_reels=[all_input_reels["reel_java_meme"]],
        )
    assert "No eligible candidates survived" in str(exc.value)


def test_deterministic_repeated_execution(
    default_engine: ScrollSenseEngine,
    all_input_reels: dict[str, Reel],
):
    """Test 7: Repeated execution with identical inputs produces identical recommendations and traces."""
    trap_inputs = [
        all_input_reels["reel_java_meme"],
        all_input_reels["reel_swe_lifestyle"],
        all_input_reels["reel_interview_joke"],
        all_input_reels["reel_laptop_comparison"],
    ]

    fixed_time = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    run_1 = default_engine.recommend_full(student_id="student_repro", input_reels=trap_inputs, generated_at=fixed_time)
    run_2 = default_engine.recommend_full(student_id="student_repro", input_reels=trap_inputs, generated_at=fixed_time)

    assert run_1.model_dump() == run_2.model_dump()


def test_all_eight_required_output_fields_are_populated(
    default_engine: ScrollSenseEngine,
    all_input_reels: dict[str, Reel],
):
    """Test 8: Ensure every single required output contract field is present and non-empty."""
    trap_inputs = [
        all_input_reels["reel_java_meme"],
        all_input_reels["reel_swe_lifestyle"],
    ]

    output = default_engine.recommend(student_id="student_contract", input_reels=trap_inputs)

    # 1. CURRENT REEL
    assert output.current_reel is not None and len(output.current_reel.strip()) > 0
    assert "reel_swe_lifestyle" in output.current_reel

    # 2. INTEREST DETECTED
    assert output.interest_detected is not None and len(output.interest_detected.strip()) > 0
    assert output.interest_detected == "Software Engineer"

    # 3. WHY
    assert output.why is not None and len(output.why.strip()) > 0
    assert "reel_java_meme" in output.why

    # 4. RECOMMENDED TECH REEL
    assert output.recommended_tech_reel is not None and len(output.recommended_tech_reel.strip()) > 0

    # 5. CATEGORY
    assert isinstance(output.category, TechCategory)

    # 6. WHY THIS RECOMMENDATION
    assert output.why_this_recommendation is not None and len(output.why_this_recommendation.strip()) > 0
    assert "Recommended via" in output.why_this_recommendation

    # 7. DIFFICULTY
    assert isinstance(output.difficulty, DepthLevel)

    # 8. CONFIDENCE
    assert isinstance(output.confidence, ConfidenceBucket)


def test_runner_up_confidence_margin_regression():
    """Test 9: Verify confidence derivation reacts deterministically to winner/runner-up ranking score margins."""
    from scrollsense.domain.candidates import Candidate
    from scrollsense.domain.enums import RetrievalSource
    from scrollsense.domain.persona import InterestState
    from scrollsense.domain.ranking import ObjectiveScores
    from scrollsense.ranking.models import RankedCandidate
    from scrollsense.selection import DeterministicExplainer, SelectionPolicy

    explainer = DeterministicExplainer(SelectionPolicy(high_confidence_min_margin=0.06, medium_confidence_min_margin=0.02))

    state = InterestState(
        student_id="test_margin",
        professional_identity={"software_engineer": 0.90},
        domains={"java": 0.80},
        goals={"career_prep": 0.85},
        depth={},
        content_preference={},
        evidence=["r1", "r2", "r3", "r4"],
        updated_at=datetime.now(timezone.utc),
    )

    def make_ranked(reel_id: str, score: float) -> RankedCandidate:
        from scrollsense.domain.gates import GateResult, HypeScore, QualityScore, SafetyResult
        from scrollsense.ranking.models import RankingTrace
        from scrollsense.ranking.weights import RankingWeights

        obj_scores = ObjectiveScores(
            topical_fit=0.8,
            difficulty_match=0.8,
            career_relevance=0.8,
            novelty=0.8,
            quality=0.8,
            hype_penalty=0.0,
            final_score=score,
        )
        gate_res = GateResult(
            candidate_id=reel_id,
            passed=True,
            safety=SafetyResult(passed=True),
            quality=QualityScore(concept_anchor_score=0.8, depth_score=0.8),
            hype=HypeScore(pattern_penalty=0.0, promotional_language_score=0.0),
        )
        trace = RankingTrace(
            candidate_id=reel_id,
            eligible=True,
            objective_scores=obj_scores,
            weights=RankingWeights(),
            weighted_contributions={},
            final_score=score,
            gate_result=gate_res,
        )
        return RankedCandidate(
            candidate=Candidate(reel_id=reel_id, source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT),
            final_score=score,
            scores=obj_scores,
            trace=trace,
        )

    winner = make_ranked("cand_1", 0.90)

    # High confidence: margin = 0.90 - 0.82 = 0.08 (>= 0.06)
    runner_up_high = make_ranked("cand_2", 0.82)
    assert explainer.derive_confidence(state, winner, runner_up_high) == ConfidenceBucket.HIGH

    # Medium confidence: margin = 0.90 - 0.86 = 0.04 (>= 0.02 and < 0.06)
    runner_up_med = make_ranked("cand_2", 0.86)
    assert explainer.derive_confidence(state, winner, runner_up_med) == ConfidenceBucket.MEDIUM

    # Low confidence: margin = 0.90 - 0.89 = 0.01 (< 0.02)
    runner_up_low = make_ranked("cand_2", 0.89)
    assert explainer.derive_confidence(state, winner, runner_up_low) == ConfidenceBucket.LOW

    # Single candidate case: uses policy default single candidate margin (0.08 -> High)
    assert explainer.derive_confidence(state, winner, runner_up_candidate=None) == ConfidenceBucket.HIGH

