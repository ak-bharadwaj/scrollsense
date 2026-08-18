"""End-to-end integration and checkpoint tests for ScrollSense semantic pipeline."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import pytest
from pydantic import BaseModel

from scrollsense.domain.enums import RetrievalSource
from scrollsense.domain.reels import Reel
from scrollsense.graph.loader import GraphLoader
from scrollsense.persona.inferencer import PersonaInferencer
from scrollsense.pipeline import PipelineResult, SemanticPipelineRunner
from scrollsense.retrieval.repository import CandidateRepository
from scrollsense.retrieval.retriever import MultiSourceRetriever
from scrollsense.signals.extractor import DeterministicSignalExtractor
from scrollsense.signals.llm_extractor import LLMStructuredSignalExtractor

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUTS_PATH = DATA_DIR / "inputs.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"
GRAPH_PATH = DATA_DIR / "identity_skill_graph.json"


class MockLLMProvider:
    """Deterministic Mock LLMProvider for reproducible pipeline testing."""

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
def graph_store():
    return GraphLoader.load_from_json(GRAPH_PATH)


@pytest.fixture
def candidate_repository():
    return CandidateRepository.load_from_json(CANDIDATES_PATH)


@pytest.fixture
def input_reels_dict() -> dict[str, Reel]:
    reels: dict[str, Reel] = {}
    with open(INPUTS_PATH, "r", encoding="utf-8") as f:
        for item in json.load(f):
            r = Reel.model_validate(item)
            reels[r.reel_id] = r
    return reels


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
        "reel_gaming_clip": {
            "topic": "gaming_clip",
            "format": "gameplay_clip",
            "tone": "energetic",
            "depth": "Beginner",
            "concept_tags": ["fps_gaming", "esports"],
            "interest_evidence": [
                {"evidence_type": "topic_implies_identity", "value": "gamer", "weight": 0.90},
                {"evidence_type": "domain_signal", "value": "gaming", "weight": 0.90},
            ],
        },
        "reel_ai_prompt_hacks": {
            "topic": "ai_prompt_hacks",
            "format": "screencast",
            "tone": "informative",
            "depth": "Beginner",
            "concept_tags": ["prompt_engineering", "ai_tools"],
            "interest_evidence": [
                {"evidence_type": "domain_signal", "value": "ai", "weight": 0.75},
                {"evidence_type": "topic_implies_identity", "value": "software_engineer", "weight": 0.60},
            ],
        },
    }
    return MockLLMProvider(trap_responses)


def test_end_to_end_canonical_swe_trap_pipeline(
    graph_store,
    candidate_repository,
    input_reels_dict,
    mock_trap_provider,
):
    """End-to-end Test 1: Canonical SWE trap sequence correctly inferred and retrieves broad identity-adjacent tech."""
    extractor = LLMStructuredSignalExtractor(mock_trap_provider, graph=graph_store)
    inferencer = PersonaInferencer()
    retriever = MultiSourceRetriever(graph_store=graph_store, repository=candidate_repository)
    pipeline = SemanticPipelineRunner(extractor=extractor, inferencer=inferencer, retriever=retriever)

    trap_reels = [
        input_reels_dict["reel_java_meme"],
        input_reels_dict["reel_swe_lifestyle"],
        input_reels_dict["reel_interview_joke"],
        input_reels_dict["reel_laptop_comparison"],
    ]

    result: PipelineResult = pipeline.run("student_canonical_trap", trap_reels)

    # 1. Verify PipelineResult structural properties
    assert result.student_id == "student_canonical_trap"
    assert len(result.input_reel_ids) == 4
    assert len(result.extracted_signals) == 4

    # 2. Verify Persona inference outputs
    state = result.interest_state
    assert state.professional_identity["software_engineer"] >= 0.80
    assert "java" in state.domains
    assert "java" not in state.professional_identity, "Java must remain a domain signal, NOT a professional identity"
    assert "career_prep" in state.goals
    assert state.goals["career_prep"] >= 0.50

    for ident, w in state.professional_identity.items():
        assert 0.0 <= w <= 1.0
    for dom, w in state.domains.items():
        assert 0.0 <= w <= 1.0

    # 3. Verify Candidate Retrieval (demonstrates escaping literal-topic trap)
    candidate_ids = result.candidate_ids
    assert len(candidate_ids) > 0

    # Identity-adjacent technical expansions reached via graph traversal (Source B / C)
    assert "reel_hld_caching" in candidate_ids, "Should retrieve System Design / HLD candidate"
    assert "reel_dsa_trees" in candidate_ids, "Should retrieve DSA candidate"
    assert "reel_cloud_k8s" in candidate_ids, "Should retrieve Cloud / Kubernetes candidate"
    assert "reel_security_auth" in candidate_ids, "Should retrieve Cybersecurity candidate"

    # Literal topic baseline candidate also retrieved via Source A
    assert "reel_java_syntax_basics" in candidate_ids, "Literal Java candidate should be retrievable via topical Source A"

    # Verify provenance and sources
    sources_map = result.candidate_sources
    assert RetrievalSource.SOURCE_B_IDENTITY_ADJACENT in sources_map["reel_hld_caching"]
    assert RetrievalSource.SOURCE_A_TOPICAL in sources_map["reel_java_syntax_basics"]


def test_end_to_end_gaming_non_trap_pipeline(
    graph_store,
    candidate_repository,
    input_reels_dict,
    mock_trap_provider,
):
    """End-to-end Test 2: Gaming history isolates to gamer persona and NEVER retrieves SWE candidates."""
    extractor = LLMStructuredSignalExtractor(mock_trap_provider, graph=graph_store)
    inferencer = PersonaInferencer()
    retriever = MultiSourceRetriever(graph_store=graph_store, repository=candidate_repository)
    pipeline = SemanticPipelineRunner(extractor=extractor, inferencer=inferencer, retriever=retriever)

    gaming_reels = [input_reels_dict["reel_gaming_clip"]]
    result = pipeline.run("student_gamer", gaming_reels)

    state = result.interest_state
    assert "gamer" in state.professional_identity
    assert "software_engineer" not in state.professional_identity
    assert "backend_developer" not in state.professional_identity

    candidate_ids = result.candidate_ids
    assert "reel_hld_caching" not in candidate_ids
    assert "reel_dsa_trees" not in candidate_ids
    assert "reel_cloud_k8s" not in candidate_ids
    assert "reel_security_auth" not in candidate_ids


def test_end_to_end_ai_hype_inclusion_before_gate(
    graph_store,
    candidate_repository,
    input_reels_dict,
    mock_trap_provider,
):
    """End-to-end Test 3: AI hype content remains in candidate pool before gate evaluation."""
    extractor = LLMStructuredSignalExtractor(mock_trap_provider, graph=graph_store)
    inferencer = PersonaInferencer()
    retriever = MultiSourceRetriever(graph_store=graph_store, repository=candidate_repository)
    pipeline = SemanticPipelineRunner(extractor=extractor, inferencer=inferencer, retriever=retriever)

    ai_reels = [input_reels_dict["reel_ai_prompt_hacks"]]
    result = pipeline.run("student_ai", ai_reels)

    candidate_ids = result.candidate_ids
    assert "reel_ai_hype_trap" in candidate_ids, "Hype candidate must be preserved at retrieval stage for later gate evaluation"


def test_pipeline_determinism_with_deterministic_extractor(
    graph_store,
    candidate_repository,
    input_reels_dict,
):
    """End-to-end Test 4: Pipeline execution with DeterministicSignalExtractor is strictly reproducible."""
    extractor = DeterministicSignalExtractor()
    inferencer = PersonaInferencer()
    retriever = MultiSourceRetriever(graph_store=graph_store, repository=candidate_repository)
    pipeline = SemanticPipelineRunner(extractor=extractor, inferencer=inferencer, retriever=retriever)

    trap_reels = [
        input_reels_dict["reel_java_meme"],
        input_reels_dict["reel_swe_lifestyle"],
        input_reels_dict["reel_interview_joke"],
        input_reels_dict["reel_laptop_comparison"],
    ]

    fixed_time = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    run_1 = pipeline.run("student_det", trap_reels, generated_at=fixed_time)
    run_2 = pipeline.run("student_det", trap_reels, generated_at=fixed_time)

    assert run_1.model_dump() == run_2.model_dump()
