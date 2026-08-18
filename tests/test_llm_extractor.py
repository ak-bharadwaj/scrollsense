"""Unit and integration tests for LLMStructuredSignalExtractor and provider abstraction."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import pytest
from pydantic import BaseModel

from scrollsense.domain.enums import DepthLevel, EvidenceType
from scrollsense.domain.reels import Reel, ReelSignal
from scrollsense.persona import PersonaInferencer
from scrollsense.signals import (
    DeterministicSignalExtractor,
    ExtractionError,
    ExtractionValidationError,
    LLMProvider,
    LLMProviderError,
    LLMStructuredSignalExtractor,
    SignalExtractor,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUTS_PATH = DATA_DIR / "inputs.json"


class MockLLMProvider:
    """Mock LLMProvider returning programmed structured responses or raising errors."""

    def __init__(self, responses: dict[str, Any] | None = None, model_name: str = "mock-llm-v1") -> None:
        self._responses = responses or {}
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_structured_json(self, prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
        for reel_id, response in self._responses.items():
            if f"- Reel ID: {reel_id}" in prompt:
                if isinstance(response, Exception):
                    raise response
                return response
        raise RuntimeError("No programmed mock response found for prompt")


@pytest.fixture
def input_reels() -> dict[str, Reel]:
    """Fixture providing input reels by ID."""
    reels: dict[str, Reel] = {}
    with open(INPUTS_PATH, "r", encoding="utf-8") as f:
        for item in json.load(f):
            r = Reel.model_validate(item)
            reels[r.reel_id] = r
    return reels


def test_signal_extractor_protocol_conformance():
    """Verify that both Deterministic and LLM extractors satisfy the SignalExtractor protocol."""
    det_extractor = DeterministicSignalExtractor()
    llm_extractor = LLMStructuredSignalExtractor(MockLLMProvider())

    assert isinstance(det_extractor, SignalExtractor)
    assert isinstance(llm_extractor, SignalExtractor)


def test_valid_llm_structured_extraction(input_reels: dict[str, Reel]):
    """Verify LLM extractor parses valid structured JSON into typed ReelSignal."""
    mock_response = {
        "topic": "java_meme",
        "format": "meme",
        "tone": "humorous",
        "depth": "Beginner",
        "concept_tags": ["java", "exception_handling"],
        "interest_evidence": [
            {
                "evidence_type": "topic_implies_identity",
                "value": "software_engineer",
                "weight": 0.65,
            },
            {
                "evidence_type": "domain_signal",
                "value": "java",
                "weight": 0.80,
            },
        ],
    }
    provider = MockLLMProvider({"reel_java_meme": mock_response})
    extractor = LLMStructuredSignalExtractor(provider)

    signal = extractor.extract(input_reels["reel_java_meme"])

    assert isinstance(signal, ReelSignal)
    assert signal.reel_id == "reel_java_meme"
    assert signal.topic == "java_meme"
    assert signal.model_version == "mock-llm-v1"
    assert len(signal.interest_evidence) == 2
    assert signal.interest_evidence[0].evidence_type == EvidenceType.TOPIC_IMPLIES_IDENTITY
    assert signal.interest_evidence[0].value == "software_engineer"


def test_llm_extractor_rejects_unsupported_identity(input_reels: dict[str, Reel]):
    """Verify LLM extractor rejects unsupported identity values via post-LLM validation."""
    mock_response = {
        "topic": "laptop_comparison",
        "format": "hardware_comparison",
        "tone": "technical",
        "depth": "Intermediate",
        "concept_tags": ["hardware", "docker"],
        "interest_evidence": [
            {
                "evidence_type": "professional_identity_signal",
                "value": "unsupported_astronaut_identity",
                "weight": 0.70,
            }
        ],
    }
    provider = MockLLMProvider({"reel_laptop_comparison": mock_response})
    extractor = LLMStructuredSignalExtractor(provider)

    with pytest.raises(ExtractionValidationError) as exc:
        extractor.extract(input_reels["reel_laptop_comparison"])
    assert "emitted unsupported identity" in str(exc.value)


def test_llm_extractor_rejects_invalid_career_stage(input_reels: dict[str, Reel]):
    """Verify LLM extractor rejects unsupported career stage values."""
    mock_response = {
        "topic": "interview_joke",
        "format": "interview_joke",
        "tone": "humorous",
        "depth": "Beginner",
        "concept_tags": ["dsa"],
        "interest_evidence": [
            {
                "evidence_type": "career_stage_signal",
                "value": "invalid_executive_stage",
                "weight": 0.80,
            }
        ],
    }
    provider = MockLLMProvider({"reel_interview_joke": mock_response})
    extractor = LLMStructuredSignalExtractor(provider)

    with pytest.raises(ExtractionValidationError) as exc:
        extractor.extract(input_reels["reel_interview_joke"])
    assert "emitted unsupported career stage" in str(exc.value)


def test_llm_extractor_rejects_out_of_bounds_weights(input_reels: dict[str, Reel]):
    """Verify LLM extractor rejects weights > 1.0 or < 0.0."""
    mock_response = {
        "topic": "java_meme",
        "format": "meme",
        "tone": "humorous",
        "depth": "Beginner",
        "concept_tags": ["java"],
        "interest_evidence": [
            {
                "evidence_type": "domain_signal",
                "value": "java",
                "weight": 1.5,
            }
        ],
    }
    provider = MockLLMProvider({"reel_java_meme": mock_response})
    extractor = LLMStructuredSignalExtractor(provider)

    with pytest.raises(ExtractionValidationError):
        extractor.extract(input_reels["reel_java_meme"])


def test_llm_extractor_handles_provider_error(input_reels: dict[str, Reel]):
    """Verify LLM extractor handles provider timeout or network failures cleanly."""
    provider = MockLLMProvider({"reel_java_meme": LLMProviderError("Connection timeout to LLM endpoint")})
    extractor = LLMStructuredSignalExtractor(provider)

    with pytest.raises(ExtractionError) as exc:
        extractor.extract(input_reels["reel_java_meme"])
    assert "LLM provider failed" in str(exc.value)


def test_trap_pipeline_integration_with_llm_signals(input_reels: dict[str, Reel]):
    """Integration test: Extract signals for 4 trap reels via LLM and feed into PersonaInferencer."""
    trap_responses = {
        "reel_java_meme": {
            "topic": "java_meme",
            "format": "meme",
            "tone": "humorous",
            "depth": "Beginner",
            "concept_tags": ["java", "debugging"],
            "interest_evidence": [
                {"evidence_type": "topic_implies_identity", "value": "software_engineer", "weight": 0.65},
                {"evidence_type": "domain_signal", "value": "java", "weight": 0.80},
            ],
        },
        "reel_swe_lifestyle": {
            "topic": "swe_lifestyle",
            "format": "vlog",
            "tone": "casual",
            "depth": "Beginner",
            "concept_tags": ["software_engineering", "workplace"],
            "interest_evidence": [
                {"evidence_type": "topic_implies_identity", "value": "software_engineer", "weight": 0.85},
                {"evidence_type": "professional_identity_signal", "value": "backend_developer", "weight": 0.80},
            ],
        },
        "reel_interview_joke": {
            "topic": "interview_joke",
            "format": "interview_joke",
            "tone": "humorous",
            "depth": "Beginner",
            "concept_tags": ["dsa", "interview_prep"],
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
            "concept_tags": ["hardware", "docker"],
            "interest_evidence": [
                {"evidence_type": "professional_identity_signal", "value": "software_engineer", "weight": 0.70},
                {"evidence_type": "domain_signal", "value": "hardware", "weight": 0.60},
            ],
        },
    }

    provider = MockLLMProvider(trap_responses, model_name="gemini-2.0-flash")
    llm_extractor = LLMStructuredSignalExtractor(provider)
    inferencer = PersonaInferencer()

    trap_reel_ids = [
        "reel_java_meme",
        "reel_swe_lifestyle",
        "reel_interview_joke",
        "reel_laptop_comparison",
    ]
    signals = [llm_extractor.extract(input_reels[r_id]) for r_id in trap_reel_ids]

    state = inferencer.infer_interest_state("student_llm_trap", signals)

    assert state.professional_identity["software_engineer"] >= 0.80
    assert "career_prep" in state.goals
    assert "java" in state.domains
    assert "java" not in state.professional_identity
    assert len(state.evidence) == 4
