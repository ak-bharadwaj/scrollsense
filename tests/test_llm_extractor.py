"""Unit and integration tests for LLMStructuredSignalExtractor and concrete Gemini provider."""

import io
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
import urllib.error
import pytest
from pydantic import BaseModel

from scrollsense.domain.enums import DepthLevel, EvidenceType, NodeType
from scrollsense.domain.graph import IdentitySkillGraph
from scrollsense.domain.reels import Reel, ReelSignal
from scrollsense.graph import GraphStore
from scrollsense.persona import PersonaInferencer
from scrollsense.signals import (
    DeterministicSignalExtractor,
    ExtractionError,
    ExtractionValidationError,
    GeminiLLMProvider,
    LLMConfig,
    LLMProviderError,
    LLMStructuredSignalExtractor,
    SignalExtractor,
    StructuredExtractionPayload,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUTS_PATH = DATA_DIR / "inputs.json"
GRAPH_PATH = DATA_DIR / "identity_skill_graph.json"


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
def canonical_graph() -> IdentitySkillGraph:
    """Fixture providing parsed canonical IdentitySkillGraph."""
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    core = {
        "version": raw_data["version"],
        "nodes": raw_data["nodes"],
        "edges": raw_data["edges"],
    }
    return IdentitySkillGraph.model_validate(core)


@pytest.fixture
def graph_store(canonical_graph: IdentitySkillGraph) -> GraphStore:
    """Fixture providing GraphStore representation."""
    return GraphStore(canonical_graph)


@pytest.fixture
def input_reels() -> dict[str, Reel]:
    """Fixture providing input reels by ID."""
    reels: dict[str, Reel] = {}
    with open(INPUTS_PATH, "r", encoding="utf-8") as f:
        for item in json.load(f):
            r = Reel.model_validate(item)
            reels[r.reel_id] = r
    return reels


def test_default_gemini_model_is_current_and_supported():
    """Verify default Gemini model is gemini-3.5-flash and not a deprecated model."""
    config = LLMConfig()
    assert config.model_name == "gemini-3.5-flash"
    assert config.model_name not in ["gemini-1.0-pro", "gemini-1.5-flash", "chat-bison", "text-bison-001"]


def test_signal_extractor_protocol_conformance(canonical_graph: IdentitySkillGraph):
    """Verify that both Deterministic and LLM extractors satisfy the SignalExtractor protocol."""
    det_extractor = DeterministicSignalExtractor()
    llm_extractor = LLMStructuredSignalExtractor(MockLLMProvider(), graph=canonical_graph)

    assert isinstance(det_extractor, SignalExtractor)
    assert isinstance(llm_extractor, SignalExtractor)


def test_llm_extractor_derives_allowlists_from_graph_domain_model(canonical_graph: IdentitySkillGraph):
    """Verify the extractor derives allowed identities and career stages directly from IdentitySkillGraph."""
    extractor = LLMStructuredSignalExtractor(MockLLMProvider(), graph=canonical_graph)

    assert extractor.allowed_identities == {"software_engineer", "backend_developer", "gamer"}
    assert extractor.allowed_career_stages == {"candidate"}


def test_llm_extractor_derives_allowlists_from_graph_store(graph_store: GraphStore):
    """Verify the extractor derives allowed identities from GraphStore via public APIs without private access."""
    extractor = LLMStructuredSignalExtractor(MockLLMProvider(), graph=graph_store)

    assert extractor.allowed_identities == {"software_engineer", "backend_developer", "gamer"}
    assert extractor.allowed_career_stages == {"candidate"}


def test_graph_store_public_query_apis(graph_store: GraphStore):
    """Verify GraphStore public query APIs get_nodes_by_category and get_nodes_by_type."""
    identities_cat = graph_store.get_nodes_by_category(NodeType.PROFESSIONAL_IDENTITY)
    identities_type = graph_store.get_nodes_by_type(NodeType.PROFESSIONAL_IDENTITY)

    assert len(identities_cat) == 3
    assert {n.id for n in identities_cat} == {"software_engineer", "backend_developer", "gamer"}
    assert identities_cat == identities_type


def test_valid_llm_structured_extraction(input_reels: dict[str, Reel], canonical_graph: IdentitySkillGraph):
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
    extractor = LLMStructuredSignalExtractor(provider, graph=canonical_graph)

    signal = extractor.extract(input_reels["reel_java_meme"])

    assert isinstance(signal, ReelSignal)
    assert signal.reel_id == "reel_java_meme"
    assert signal.topic == "java_meme"
    assert signal.model_version == "mock-llm-v1"
    assert len(signal.interest_evidence) == 2
    assert signal.interest_evidence[0].evidence_type == EvidenceType.TOPIC_IMPLIES_IDENTITY
    assert signal.interest_evidence[0].value == "software_engineer"


def test_llm_extractor_rejects_unsupported_identity(input_reels: dict[str, Reel], canonical_graph: IdentitySkillGraph):
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
    extractor = LLMStructuredSignalExtractor(provider, graph=canonical_graph)

    with pytest.raises(ExtractionValidationError) as exc:
        extractor.extract(input_reels["reel_laptop_comparison"])
    assert "emitted unsupported identity" in str(exc.value)


def test_llm_extractor_rejects_invalid_career_stage(input_reels: dict[str, Reel], canonical_graph: IdentitySkillGraph):
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
    extractor = LLMStructuredSignalExtractor(provider, graph=canonical_graph)

    with pytest.raises(ExtractionValidationError) as exc:
        extractor.extract(input_reels["reel_interview_joke"])
    assert "emitted unsupported career stage" in str(exc.value)


def test_llm_extractor_rejects_out_of_bounds_weights(input_reels: dict[str, Reel], canonical_graph: IdentitySkillGraph):
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
    extractor = LLMStructuredSignalExtractor(provider, graph=canonical_graph)

    with pytest.raises(ExtractionValidationError):
        extractor.extract(input_reels["reel_java_meme"])


def test_llm_extractor_handles_provider_error(input_reels: dict[str, Reel], canonical_graph: IdentitySkillGraph):
    """Verify LLM extractor handles provider timeout or network failures cleanly."""
    provider = MockLLMProvider({"reel_java_meme": LLMProviderError("Connection timeout to LLM endpoint")})
    extractor = LLMStructuredSignalExtractor(provider, graph=canonical_graph)

    with pytest.raises(ExtractionError) as exc:
        extractor.extract(input_reels["reel_java_meme"])
    assert "LLM provider failed" in str(exc.value)


def test_gemini_provider_mock_transport_success():
    """Verify concrete GeminiLLMProvider generates and extracts structured response."""
    config = LLMConfig(provider_name="gemini", model_name="gemini-3.5-flash", api_key="test_api_key", timeout_seconds=10.0)
    provider = GeminiLLMProvider(config)

    gemini_api_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "topic": "java_meme",
                                "format": "meme",
                                "tone": "humorous",
                                "depth": "Beginner",
                                "concept_tags": ["java"],
                                "interest_evidence": [
                                    {"evidence_type": "domain_signal", "value": "java", "weight": 0.8}
                                ],
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(gemini_api_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        result = provider.generate_structured_json("test prompt", StructuredExtractionPayload)
        assert result["topic"] == "java_meme"
        assert result["depth"] == "Beginner"
        mock_urlopen.assert_called_once()


def test_gemini_provider_missing_api_key():
    """Verify concrete GeminiLLMProvider raises LLMProviderError on missing API key."""
    config = LLMConfig(provider_name="gemini", model_name="gemini-3.5-flash", api_key=None)
    provider = GeminiLLMProvider(config)

    with pytest.raises(LLMProviderError) as exc:
        provider.generate_structured_json("test prompt", StructuredExtractionPayload)
    assert "Missing API key" in str(exc.value)


def test_gemini_provider_http_error_handling():
    """Verify concrete GeminiLLMProvider handles HTTP errors cleanly."""
    config = LLMConfig(provider_name="gemini", model_name="gemini-3.5-flash", api_key="key")
    provider = GeminiLLMProvider(config)

    http_err = urllib.error.HTTPError(
        url="http://test",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b'{"error": "Invalid API key"}'),
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(LLMProviderError) as exc:
            provider.generate_structured_json("test prompt", StructuredExtractionPayload)
        assert "HTTP error 401" in str(exc.value)


def test_llm_config_from_env_valid(monkeypatch: pytest.MonkeyPatch):
    """Verify LLMConfig loads correctly from environment variables including GEMINI_MODEL and GEMINI_API_KEY."""
    monkeypatch.setenv("SCROLLSENSE_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "env_secret_key")
    monkeypatch.setenv("SCROLLSENSE_LLM_TIMEOUT", "25.5")

    config = LLMConfig.from_env()
    assert config.provider_name == "gemini"
    assert config.model_name == "gemini-1.5-flash"
    assert config.api_key == "env_secret_key"
    assert config.timeout_seconds == 25.5


def test_llm_config_from_env_invalid_timeout(monkeypatch: pytest.MonkeyPatch):
    """Verify LLMConfig rejects invalid timeout strings explicitly rather than falling back silently."""
    monkeypatch.setenv("SCROLLSENSE_LLM_TIMEOUT", "invalid_not_a_number")

    with pytest.raises(ValueError) as exc:
        LLMConfig.from_env()
    assert "Invalid SCROLLSENSE_LLM_TIMEOUT" in str(exc.value)


def test_trap_pipeline_integration_with_llm_signals(input_reels: dict[str, Reel], canonical_graph: IdentitySkillGraph):
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

    provider = MockLLMProvider(trap_responses, model_name="gemini-3.5-flash")
    llm_extractor = LLMStructuredSignalExtractor(provider, graph=canonical_graph)
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


def test_real_gemini_integration_skips_cleanly_without_credentials(canonical_graph: IdentitySkillGraph):
    """Optional real integration test for Gemini API; skips cleanly if GEMINI_API_KEY is not configured."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("Skipping real Gemini API integration test: GEMINI_API_KEY not configured")

    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    config = LLMConfig(provider_name="gemini", model_name=model, api_key=api_key)
    provider = GeminiLLMProvider(config=config)

    reel = Reel(
        reel_id="test_real_gemini",
        title="Understanding QuickSort Algorithm in Python",
        category="coding",
        depth=DepthLevel.BEGINNER,
        transcript="QuickSort selects a pivot element and partitions arrays recursively.",
        concept_tags=["quicksort", "algorithms"],
    )

    extractor = LLMStructuredSignalExtractor(provider=provider, graph=canonical_graph)
    try:
        signal = extractor.extract(reel)
    except ExtractionError as exc:
        if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc) or "quota" in str(exc).lower():
            pytest.skip(f"Skipping live Gemini test due to Free Tier quota rate-limit: {exc}")
        raise

    assert signal.reel_id == "test_real_gemini"
    assert signal.topic is not None

