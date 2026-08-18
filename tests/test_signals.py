"""Unit tests for deterministic semantic ReelSignal extraction and graph contract alignment."""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from scrollsense.domain.enums import DepthLevel, EvidenceType, NodeType
from scrollsense.domain.graph import IdentitySkillGraph
from scrollsense.domain.reels import Reel, ReelSignal
from scrollsense.signals import (
    MODEL_VERSION,
    ONTOLOGY_VERSION,
    SIGNAL_VERSION,
    DeterministicSignalExtractor,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUTS_PATH = DATA_DIR / "inputs.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"
GRAPH_PATH = DATA_DIR / "identity_skill_graph.json"


@pytest.fixture
def extractor() -> DeterministicSignalExtractor:
    """Fixture providing initialized DeterministicSignalExtractor."""
    return DeterministicSignalExtractor()


@pytest.fixture
def all_reels() -> dict[str, Reel]:
    """Fixture providing dictionary of all test reels by ID."""
    reels: dict[str, Reel] = {}
    with open(INPUTS_PATH, "r", encoding="utf-8") as f:
        for item in json.load(f):
            r = Reel.model_validate(item)
            reels[r.reel_id] = r
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for item in json.load(f):
            r = Reel.model_validate(item)
            reels[r.reel_id] = r
    return reels


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


def test_cross_module_evidence_matches_canonical_graph_nodes(
    extractor: DeterministicSignalExtractor,
    all_reels: dict[str, Reel],
    canonical_graph: IdentitySkillGraph,
):
    """Cross-module validation: every emitted identity/stage evidence value must exist in canonical graph."""
    valid_identities = {n.id for n in canonical_graph.nodes if n.category == NodeType.PROFESSIONAL_IDENTITY}
    valid_career_stages = {n.id for n in canonical_graph.nodes if n.category == NodeType.CAREER_STAGE}

    assert len(valid_identities) > 0
    assert len(valid_career_stages) > 0

    for reel in all_reels.values():
        signal = extractor.extract(reel)
        for ev in signal.interest_evidence:
            if ev.evidence_type in (EvidenceType.TOPIC_IMPLIES_IDENTITY, EvidenceType.PROFESSIONAL_IDENTITY_SIGNAL):
                assert ev.value in valid_identities, (
                    f"Reel '{reel.reel_id}' emitted invalid professional_identity evidence '{ev.value}'. "
                    f"Allowed graph identities: {valid_identities}"
                )
            elif ev.evidence_type == EvidenceType.CAREER_STAGE_SIGNAL:
                assert ev.value in valid_career_stages, (
                    f"Reel '{reel.reel_id}' emitted invalid career_stage evidence '{ev.value}'. "
                    f"Allowed graph stages: {valid_career_stages}"
                )


def test_java_meme_signal_extraction(extractor: DeterministicSignalExtractor, all_reels: dict[str, Reel]):
    """Test extraction on Java meme reel produces moderate SWE evidence + Java domain evidence."""
    reel = all_reels["reel_java_meme"]
    signal = extractor.extract(reel)

    assert isinstance(signal, ReelSignal)
    assert signal.reel_id == "reel_java_meme"
    assert signal.topic == "java_meme"
    assert signal.depth == DepthLevel.BEGINNER

    evidence_map = {(e.evidence_type, e.value): e.weight for e in signal.interest_evidence}
    assert (EvidenceType.TOPIC_IMPLIES_IDENTITY, "software_engineer") in evidence_map
    assert 0.5 <= evidence_map[(EvidenceType.TOPIC_IMPLIES_IDENTITY, "software_engineer")] <= 0.8
    assert (EvidenceType.DOMAIN_SIGNAL, "java") in evidence_map


def test_swe_lifestyle_signal_extraction(extractor: DeterministicSignalExtractor, all_reels: dict[str, Reel]):
    """Test extraction on SWE lifestyle reel produces strong software_engineer evidence."""
    reel = all_reels["reel_swe_lifestyle"]
    signal = extractor.extract(reel)

    assert signal.topic == "swe_lifestyle"
    evidence_map = {(e.evidence_type, e.value): e.weight for e in signal.interest_evidence}
    assert (EvidenceType.TOPIC_IMPLIES_IDENTITY, "software_engineer") in evidence_map
    assert evidence_map[(EvidenceType.TOPIC_IMPLIES_IDENTITY, "software_engineer")] >= 0.80
    assert (EvidenceType.PROFESSIONAL_IDENTITY_SIGNAL, "backend_developer") in evidence_map


def test_interview_joke_signal_extraction(extractor: DeterministicSignalExtractor, all_reels: dict[str, Reel]):
    """Test extraction on interview joke reel produces candidate stage and career_prep goal evidence."""
    reel = all_reels["reel_interview_joke"]
    signal = extractor.extract(reel)

    assert signal.topic == "interview_joke"
    evidence_map = {(e.evidence_type, e.value) for e in signal.interest_evidence}
    assert (EvidenceType.CAREER_STAGE_SIGNAL, "candidate") in evidence_map
    assert (EvidenceType.GOAL_SIGNAL, "career_prep") in evidence_map
    assert (EvidenceType.TOPIC_IMPLIES_IDENTITY, "software_engineer") in evidence_map


def test_laptop_comparison_signal_extraction(extractor: DeterministicSignalExtractor, all_reels: dict[str, Reel]):
    """Test extraction on laptop comparison reel uses graph-compatible software_engineer, not invalid developer."""
    reel = all_reels["reel_laptop_comparison"]
    signal = extractor.extract(reel)

    assert signal.topic == "laptop_comparison"
    evidence_map = {(e.evidence_type, e.value) for e in signal.interest_evidence}
    assert (EvidenceType.PROFESSIONAL_IDENTITY_SIGNAL, "software_engineer") in evidence_map
    assert (EvidenceType.DOMAIN_SIGNAL, "hardware") in evidence_map
    assert (EvidenceType.DOMAIN_SIGNAL, "cloud_infrastructure") in evidence_map

    # Ensure unsupported developer identity string is NOT emitted
    all_values = [e.value for e in signal.interest_evidence]
    assert "developer" not in all_values, "Must NOT emit unsupported 'developer' identity"


def test_gaming_clip_does_not_infer_software_engineer(extractor: DeterministicSignalExtractor, all_reels: dict[str, Reel]):
    """Test that gaming clip infers gamer identity and NEVER software_engineer."""
    reel = all_reels["reel_gaming_clip"]
    signal = extractor.extract(reel)

    assert signal.topic == "gaming_clip"
    evidence_values = [e.value for e in signal.interest_evidence]
    assert "gamer" in evidence_values
    assert "gaming" in evidence_values

    # Must NOT infer SWE / backend_developer / developer
    assert "software_engineer" not in evidence_values
    assert "backend_developer" not in evidence_values
    assert "developer" not in evidence_values
    assert "candidate" not in evidence_values


def test_ai_substantive_tutorial_signal_extraction(extractor: DeterministicSignalExtractor, all_reels: dict[str, Reel]):
    """Test extraction on grounded AI tutorial produces ai_engineering domain and SWE identity."""
    reel = all_reels["reel_ai_substance"]
    signal = extractor.extract(reel)

    evidence_map = {(e.evidence_type, e.value) for e in signal.interest_evidence}
    assert (EvidenceType.DOMAIN_SIGNAL, "ai_engineering") in evidence_map
    assert (EvidenceType.TOPIC_IMPLIES_IDENTITY, "software_engineer") in evidence_map


def test_ai_hype_signal_extraction(extractor: DeterministicSignalExtractor, all_reels: dict[str, Reel]):
    """Test extraction on AI hype clickbait produces ai domain, NOT ai_engineering or SWE identity."""
    reel = all_reels["reel_ai_hype_trap"]
    signal = extractor.extract(reel)

    evidence_map = {(e.evidence_type, e.value) for e in signal.interest_evidence}
    assert (EvidenceType.DOMAIN_SIGNAL, "ai") in evidence_map
    assert (EvidenceType.GOAL_SIGNAL, "career_shortcuts") in evidence_map

    evidence_values = [e.value for e in signal.interest_evidence]
    assert "ai_engineering" not in evidence_values
    assert "software_engineer" not in evidence_values


def test_version_metadata_and_determinism(extractor: DeterministicSignalExtractor, all_reels: dict[str, Reel]):
    """Test explicit version metadata and exact determinism on repeated extractions."""
    reel = all_reels["reel_java_meme"]
    fixed_time = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)

    signal_1 = extractor.extract(reel, generated_at=fixed_time)
    signal_2 = extractor.extract(reel, generated_at=fixed_time)

    assert signal_1.signal_version == SIGNAL_VERSION
    assert signal_1.ontology_version == ONTOLOGY_VERSION
    assert signal_1.model_version == MODEL_VERSION
    assert signal_1.model_dump() == signal_2.model_dump()
