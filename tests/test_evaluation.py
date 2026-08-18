"""Unit and integration tests for the evaluation harness, baselines, metrics, and scenarios."""

from pathlib import Path
import pytest

from scrollsense.domain.enums import TechCategory
from scrollsense.evaluation import (
    B0_LiteralTopicBaseline,
    B1_CategoryDominanceBaseline,
    B2_ScrollSenseBaseline,
    BenchmarkReportGenerator,
    BenchmarkSummary,
    EvaluationHarness,
    get_all_scenarios,
    get_evaluation_candidate_reels,
    get_evaluation_candidate_repository,
)
from scrollsense.graph.loader import GraphLoader
from scrollsense.graph.store import GraphStore

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GRAPH_PATH = DATA_DIR / "identity_skill_graph.json"


@pytest.fixture
def graph_store() -> GraphStore:
    """Fixture providing GraphStore."""
    return GraphLoader.load_from_json(GRAPH_PATH)


@pytest.fixture
def harness(graph_store: GraphStore) -> EvaluationHarness:
    """Fixture providing EvaluationHarness."""
    return EvaluationHarness(graph_store=graph_store)


def test_four_scenarios_contain_eight_reels_each():
    """Verify exactly 4 scenarios are configured and each contains exactly 8 input reels."""
    scenarios = get_all_scenarios()
    assert len(scenarios) == 4
    for sc in scenarios:
        assert len(sc.input_reels) == 8
        assert sc.ground_truth_latent_identity in ("software_engineer", "gamer")
        assert len(sc.ground_truth_target_categories) > 0


def test_candidate_pool_contains_twenty_diverse_reels():
    """Verify evaluation candidate pool contains 20 reels covering all candidate tiers."""
    candidates = get_evaluation_candidate_reels()
    assert len(candidates) == 20

    # Verify presence of hype traps
    hype_reels = [c for c in candidates if "ai_hype" in c.concept_tags or "career_shortcuts" in c.concept_tags]
    assert len(hype_reels) >= 3

    # Verify presence of unsafe items
    unsafe_reels = [c for c in candidates if "malware" in c.concept_tags]
    assert len(unsafe_reels) >= 1

    # Verify repository loading
    repo = get_evaluation_candidate_repository()
    assert repo.total_count == 20
    assert len(repo.get_all()) == 20


def test_b0_literal_topic_baseline_selects_shallow_match():
    """Verify B0 baseline picks literal topic match on Java meme input."""
    scenarios = get_all_scenarios()
    swe_scenario = scenarios[0]

    candidate_pool = get_evaluation_candidate_reels()
    b0 = B0_LiteralTopicBaseline(candidate_pool)

    # When user only watches Java meme, B0 picks literal Java syntax
    rec = b0.recommend([swe_scenario.input_reels[0]])
    assert rec.baseline_id == "B0"
    assert rec.recommended_reel_id == "reel_java_syntax_basics"
    assert rec.category == TechCategory.JAVA


def test_b1_category_dominance_baseline():
    """Verify B1 baseline picks first matching item for dominant category."""
    scenarios = get_all_scenarios()
    swe_scenario = scenarios[0]

    candidate_pool = get_evaluation_candidate_reels()
    b1 = B1_CategoryDominanceBaseline(candidate_pool)

    rec = b1.recommend(swe_scenario.input_reels)
    assert rec.baseline_id == "B1"
    assert rec.category in (TechCategory.JAVA, TechCategory.HLD, TechCategory.DSA, TechCategory.AI, TechCategory.CLOUD)


def test_full_benchmark_harness_execution(harness: EvaluationHarness):
    """Verify EvaluationHarness runs complete multi-scenario benchmark and produces report."""
    summary = harness.run_benchmark()

    assert isinstance(summary, BenchmarkSummary)
    assert len(summary.scenario_records) == 4

    # Verify aggregate metrics calculated for B0, B1, B2
    for b_id in ("B0", "B1", "B2"):
        assert b_id in summary.aggregate_metrics
        m = summary.aggregate_metrics[b_id]
        assert 0.0 <= m["trap_avoidance_rate"] <= 1.0
        assert 0.0 <= m["technology_relevance"] <= 1.0
        assert 0.0 <= m["identity_consistency"] <= 1.0
        assert 0.0 <= m["hype_rejection_rate"] <= 1.0
        assert 0.0 <= m["safety_rejection_rate"] <= 1.0
        assert 0.0 <= m["provenance_completeness"] <= 1.0
        assert 0.0 <= m["deterministic_replay"] <= 1.0
        assert 0.0 <= m["top1_expert_alignment"] <= 1.0

    # ScrollSense (B2) must achieve 100% provenance completeness, hype rejection, safety rejection, and top-1 expert alignment
    b2_m = summary.aggregate_metrics["B2"]
    assert b2_m["provenance_completeness"] == 1.0
    assert b2_m["hype_rejection_rate"] == 1.0
    assert b2_m["safety_rejection_rate"] == 1.0
    assert b2_m["deterministic_replay"] == 1.0
    assert b2_m["top1_expert_alignment"] >= 0.75

    # Verify Markdown report generation
    report_md = BenchmarkReportGenerator.generate_markdown_report(summary)
    assert "# ScrollSense Empirical Evaluation Benchmark Report" in report_md
    assert "B0: Literal Topic" in report_md
    assert "B2: ScrollSense (Ours)" in report_md
