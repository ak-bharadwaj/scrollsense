"""Unit tests for deterministic InterestState persona inference."""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from scrollsense.domain.enums import DepthLevel
from scrollsense.domain.persona import InterestState
from scrollsense.domain.reels import Reel, ReelSignal
from scrollsense.persona import InferencePolicy, PersonaInferencer
from scrollsense.signals import DeterministicSignalExtractor

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUTS_PATH = DATA_DIR / "inputs.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"


@pytest.fixture
def inferencer() -> PersonaInferencer:
    """Fixture providing initialized PersonaInferencer."""
    return PersonaInferencer()


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


def test_canonical_swe_trap_produces_software_engineer_dominance(
    inferencer: PersonaInferencer,
    extractor: DeterministicSignalExtractor,
    all_reels: dict[str, Reel],
):
    """Test 1: Heterogeneous trap sequence produces software_engineer as dominant identity."""
    trap_ids = [
        "reel_java_meme",
        "reel_swe_lifestyle",
        "reel_interview_joke",
        "reel_laptop_comparison",
    ]
    signals = [extractor.extract(all_reels[r_id]) for r_id in trap_ids]

    state = inferencer.infer_interest_state("student_trap", signals)

    assert isinstance(state, InterestState)
    assert "software_engineer" in state.professional_identity
    # Saturated multi-evidence across 4 reels yields high confidence
    assert state.professional_identity["software_engineer"] >= 0.80

    # Top identity must be software_engineer
    top_identity = list(state.professional_identity.keys())[0]
    assert top_identity == "software_engineer"


def test_java_remains_domain_not_identity(
    inferencer: PersonaInferencer,
    extractor: DeterministicSignalExtractor,
    all_reels: dict[str, Reel],
):
    """Test 2: Java is recorded in domains, NOT in professional_identity."""
    trap_ids = ["reel_java_meme", "reel_swe_lifestyle"]
    signals = [extractor.extract(all_reels[r_id]) for r_id in trap_ids]

    state = inferencer.infer_interest_state("student_java", signals)

    assert "java" in state.domains
    assert "java" not in state.professional_identity


def test_gaming_only_produces_gamer_dominance(
    inferencer: PersonaInferencer,
    extractor: DeterministicSignalExtractor,
    all_reels: dict[str, Reel],
):
    """Test 3: Gaming-only history produces gamer dominance without SWE contamination."""
    gaming_ids = ["reel_gaming_clip"]
    signals = [extractor.extract(all_reels[r_id]) for r_id in gaming_ids]

    state = inferencer.infer_interest_state("student_gamer", signals)

    assert "gamer" in state.professional_identity
    assert state.professional_identity["gamer"] >= 0.50
    assert "software_engineer" not in state.professional_identity
    assert "backend_developer" not in state.professional_identity


def test_interview_evidence_produces_career_prep_goal(
    inferencer: PersonaInferencer,
    extractor: DeterministicSignalExtractor,
    all_reels: dict[str, Reel],
):
    """Test 4: Interview joke generates career_prep goal evidence."""
    signals = [extractor.extract(all_reels["reel_interview_joke"])]

    state = inferencer.infer_interest_state("student_candidate", signals)

    assert "career_prep" in state.goals
    assert state.goals["career_prep"] >= 0.40


def test_single_weak_java_meme_does_not_dominate(
    inferencer: PersonaInferencer,
    extractor: DeterministicSignalExtractor,
    all_reels: dict[str, Reel],
):
    """Test 5: A single weak Java meme does NOT establish high confidence identity."""
    signals = [extractor.extract(all_reels["reel_java_meme"])]

    state = inferencer.infer_interest_state("student_single_meme", signals)

    # Moderate/weak weight from single observation
    assert state.professional_identity["software_engineer"] < 0.50


def test_repeated_same_reel_evidence_not_double_counted(
    inferencer: PersonaInferencer,
    extractor: DeterministicSignalExtractor,
    all_reels: dict[str, Reel],
):
    """Test 6: Duplicated identical reel signals in history do not artificially inflate evidence or content preferences."""
    single_signal = extractor.extract(all_reels["reel_java_meme"])
    duplicate_signals = [single_signal, single_signal, single_signal]

    state_single = inferencer.infer_interest_state("student_1", [single_signal])
    state_dup = inferencer.infer_interest_state("student_2", duplicate_signals)

    assert state_single.professional_identity == state_dup.professional_identity
    assert state_single.domains == state_dup.domains
    assert state_single.goals == state_dup.goals
    assert state_single.depth == state_dup.depth
    assert state_single.content_preference == state_dup.content_preference
    assert state_dup.evidence == ["reel_java_meme"]


def test_weights_strictly_within_unit_interval(
    inferencer: PersonaInferencer,
    extractor: DeterministicSignalExtractor,
    all_reels: dict[str, Reel],
):
    """Test 7: All aggregated weights remain strictly in [0.0, 1.0]."""
    all_signals = [extractor.extract(r) for r in all_reels.values()]
    state = inferencer.infer_interest_state("student_heavy", all_signals)

    for ident, w in state.professional_identity.items():
        assert 0.0 <= w <= 1.0, f"Identity {ident} weight {w} outside [0, 1]"

    for dom, w in state.domains.items():
        assert 0.0 <= w <= 1.0, f"Domain {dom} weight {w} outside [0, 1]"

    for goal, w in state.goals.items():
        assert 0.0 <= w <= 1.0, f"Goal {goal} weight {w} outside [0, 1]"

    for pref, w in state.content_preference.items():
        assert 0.0 <= w <= 1.0, f"Preference {pref} weight {w} outside [0, 1]"


def test_evidence_provenance_preserved(
    inferencer: PersonaInferencer,
    extractor: DeterministicSignalExtractor,
    all_reels: dict[str, Reel],
):
    """Test 8: InterestState.evidence preserves distinct reel IDs in appearance order."""
    sequence = [
        all_reels["reel_java_meme"],
        all_reels["reel_swe_lifestyle"],
        all_reels["reel_java_meme"],
        all_reels["reel_gaming_clip"],
    ]
    signals = [extractor.extract(r) for r in sequence]

    state = inferencer.infer_interest_state("student_prov", signals)
    assert state.evidence == ["reel_java_meme", "reel_swe_lifestyle", "reel_gaming_clip"]


def test_deterministic_repeated_inference(
    inferencer: PersonaInferencer,
    extractor: DeterministicSignalExtractor,
    all_reels: dict[str, Reel],
):
    """Test 9: Repeated inference calls with same input produce identical InterestState."""
    fixed_time = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    trap_ids = ["reel_java_meme", "reel_swe_lifestyle", "reel_interview_joke"]
    signals = [extractor.extract(all_reels[r_id]) for r_id in trap_ids]

    state_1 = inferencer.infer_interest_state("student_det", signals, updated_at=fixed_time)
    state_2 = inferencer.infer_interest_state("student_det", signals, updated_at=fixed_time)

    assert state_1.model_dump() == state_2.model_dump()


def test_empty_history_handled_gracefully(inferencer: PersonaInferencer):
    """Test 10: Empty signal sequence produces valid empty InterestState."""
    state = inferencer.infer_interest_state("student_empty", [])

    assert state.student_id == "student_empty"
    assert state.professional_identity == {}
    assert state.domains == {}
    assert state.goals == {}
    assert state.depth == {}
    assert state.content_preference == {}
    assert state.evidence == []
