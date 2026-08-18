"""Unit tests for the Three-Tier Candidate Quality, Integrity, and Safety Gate."""

import json
from pathlib import Path
import pytest

from scrollsense.domain.enums import DepthLevel
from scrollsense.domain.gates import GateResult, HypeScore, QualityScore, SafetyResult
from scrollsense.domain.reels import Reel
from scrollsense.gates import CandidateGateEvaluator

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUTS_PATH = DATA_DIR / "inputs.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"


@pytest.fixture
def evaluator() -> CandidateGateEvaluator:
    """Fixture providing initialized CandidateGateEvaluator."""
    return CandidateGateEvaluator()


@pytest.fixture
def all_reels() -> dict[str, Reel]:
    """Fixture providing dictionary of all input and candidate reels."""
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


def test_grounded_hld_reel_survives(evaluator: CandidateGateEvaluator, all_reels: dict[str, Reel]):
    """Test 1: Grounded HLD candidate passes with high substance and low hype."""
    reel = all_reels["reel_hld_caching"]
    result = evaluator.evaluate(reel)

    assert isinstance(result, GateResult)
    assert result.passed is True
    assert result.rejection_reason is None
    assert result.safety.passed is True
    assert result.quality.overall >= 0.70
    assert result.hype.overall <= 0.30


def test_grounded_ai_transformer_reel_survives(evaluator: CandidateGateEvaluator, all_reels: dict[str, Reel]):
    """Test 2: Grounded AI transformer tutorial passes with high substance and low hype."""
    reel = all_reels["reel_ai_substance"]
    result = evaluator.evaluate(reel)

    assert result.passed is True
    assert result.rejection_reason is None
    assert result.quality.overall >= 0.70
    assert result.hype.overall <= 0.30


def test_ai_hype_clickbait_is_rejected(evaluator: CandidateGateEvaluator, all_reels: dict[str, Reel]):
    """Test 3: AI job-guarantee clickbait is rejected for low substance + high hype."""
    reel = all_reels["reel_ai_hype_trap"]
    result = evaluator.evaluate(reel)

    assert result.passed is False
    assert result.safety.passed is True, "Hype is NOT a safety violation"
    assert result.rejection_reason == "low_substance_high_hype"
    assert result.quality.overall < 0.35
    assert result.hype.overall >= 0.70


def test_useful_promotional_technical_reel_survives(evaluator: CandidateGateEvaluator):
    """Test 4: High-substance technical reel with promotional tone should NOT be rejected."""
    promo_tech_reel = Reel(
        reel_id="reel_promo_tech_tool",
        title="Sponsored: Build Distributed Microservices with Kubernetes and Redis",
        category="Cloud",
        format="tutorial",
        tone="promotional",
        depth=DepthLevel.INTERMEDIATE,
        concept_tags=["kubernetes", "redis", "cloud_networking"],
        transcript="This video is sponsored by CloudTools. Let's look at cluster networking and Redis caching.",
    )
    result = evaluator.evaluate(promo_tech_reel)

    assert result.passed is True, "High substance content must not be rejected merely for promotional tone"
    assert result.rejection_reason is None
    assert result.quality.overall >= 0.70
    assert result.hype.overall >= 0.40  # Shows measured hype


def test_unsafe_content_rejected_by_safety_gate(evaluator: CandidateGateEvaluator):
    """Test 5: Explicitly unsafe content is rejected at the Safety Gate."""
    unsafe_reel = Reel(
        reel_id="reel_malware_exploit",
        title="How to install keylogger malware and bypass security",
        category="Cybersecurity",
        format="tutorial",
        tone="technical",
        depth=DepthLevel.ADVANCED,
        concept_tags=["malware", "cybersecurity"],
        transcript="Download this keylogger malware executable to hijack accounts.",
    )
    result = evaluator.evaluate(unsafe_reel)

    assert result.passed is False
    assert result.safety.passed is False
    assert "safety_violation" in (result.rejection_reason or "")


def test_gaming_reel_survives_gate(evaluator: CandidateGateEvaluator, all_reels: dict[str, Reel]):
    """Test 6: Gaming reel is not rejected merely because it is gaming."""
    reel = all_reels["reel_gaming_clip"]
    result = evaluator.evaluate(reel)

    assert result.passed is True
    assert result.safety.passed is True
    assert result.rejection_reason is None


def test_deterministic_repeated_gate_evaluation(evaluator: CandidateGateEvaluator, all_reels: dict[str, Reel]):
    """Test 7: Repeated evaluation of candidate produces identical scores and decisions."""
    reel = all_reels["reel_hld_caching"]
    res_1 = evaluator.evaluate(reel)
    res_2 = evaluator.evaluate(reel)

    assert res_1.model_dump() == res_2.model_dump()


def test_all_component_scores_bounded_in_unit_interval(evaluator: CandidateGateEvaluator, all_reels: dict[str, Reel]):
    """Test 8: Every quality and hype sub-score and composite score remains in [0.0, 1.0]."""
    for reel in all_reels.values():
        res = evaluator.evaluate(reel)

        # Quality scores
        assert 0.0 <= res.quality.concept_anchor_score <= 1.0
        assert 0.0 <= res.quality.depth_score <= 1.0
        assert 0.0 <= res.quality.overall <= 1.0

        # Hype scores
        assert 0.0 <= res.hype.pattern_penalty <= 1.0
        assert 0.0 <= res.hype.promotional_language_score <= 1.0
        assert 0.0 <= res.hype.overall <= 1.0


def test_rejection_reasons_are_explicit_and_traceable(evaluator: CandidateGateEvaluator, all_reels: dict[str, Reel]):
    """Test 9: Passing candidates have None rejection_reason; rejected candidates have clear reasons."""
    hld_res = evaluator.evaluate(all_reels["reel_hld_caching"])
    assert hld_res.passed is True
    assert hld_res.rejection_reason is None

    hype_res = evaluator.evaluate(all_reels["reel_ai_hype_trap"])
    assert hype_res.passed is False
    assert hype_res.rejection_reason == "low_substance_high_hype"
