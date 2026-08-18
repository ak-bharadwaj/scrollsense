"""Unit and integration tests for evaluation harness, baselines, metrics, scenarios, and isolation."""

from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from scrollsense.domain.enums import TechCategory
from scrollsense.domain.reels import Reel
from scrollsense.evaluation import (
    DEFAULT_SENTENCE_TRANSFORMER_MODEL,
    B0_LiteralTopicBaseline,
    B1_EmbeddingSemanticSimilarityBaseline,
    B2_ScrollSenseBaseline,
    BenchmarkReportGenerator,
    BenchmarkSummary,
    EvaluationHarness,
    FakeEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
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
def candidate_reels() -> list[Reel]:
    """Fixture providing 20 evaluation candidate reels."""
    return get_evaluation_candidate_reels()


@pytest.fixture
def fake_provider() -> FakeEmbeddingProvider:
    """Fixture providing FakeEmbeddingProvider."""
    return FakeEmbeddingProvider(fixed_dim=4)


@pytest.fixture
def harness(graph_store: GraphStore, fake_provider: FakeEmbeddingProvider) -> EvaluationHarness:
    """Fixture providing EvaluationHarness with explicitly injected FakeEmbeddingProvider."""
    return EvaluationHarness(graph_store=graph_store, embedding_provider=fake_provider)


def test_four_scenarios_contain_eight_reels_each():
    """Verify exactly 4 scenarios are configured and each contains exactly 8 input reels."""
    scenarios = get_all_scenarios()
    assert len(scenarios) == 4
    for sc in scenarios:
        assert len(sc.input_reels) == 8
        assert sc.ground_truth_latent_identity in ("software_engineer", "gamer")
        assert len(sc.ground_truth_target_categories) > 0


def test_candidate_pool_contains_twenty_diverse_reels(candidate_reels: list[Reel]):
    """Verify evaluation candidate pool contains 20 reels covering all candidate tiers."""
    assert len(candidate_reels) == 20

    # Verify presence of hype traps
    hype_reels = [c for c in candidate_reels if "ai_hype" in c.concept_tags or "career_shortcuts" in c.concept_tags]
    assert len(hype_reels) >= 3

    # Verify presence of unsafe items
    unsafe_reels = [c for c in candidate_reels if "malware" in c.concept_tags]
    assert len(unsafe_reels) >= 1

    # Verify repository loading
    repo = get_evaluation_candidate_repository()
    assert repo.total_count == 20
    assert len(repo.get_all()) == 20


def test_b0_actual_jaccard_similarity_calculation(candidate_reels: list[Reel]):
    """Verify B0 baseline calculates mathematically exact Jaccard similarity (|A ∩ B| / |A ∪ B|)."""
    # 1. Exact calculation unit test
    set_a = {"java", "backend", "docker"}
    set_b = {"java", "records", "docker"}
    # intersection = {"java", "docker"} (2), union = {"java", "backend", "docker", "records"} (4) -> 2/4 = 0.50
    assert B0_LiteralTopicBaseline.calculate_jaccard(set_a, set_b) == 0.50

    # Empty set handling
    assert B0_LiteralTopicBaseline.calculate_jaccard(set(), set_b) == 0.0
    assert B0_LiteralTopicBaseline.calculate_jaccard(set_a, set()) == 0.0

    # 2. Recommendation output test
    scenarios = get_all_scenarios()
    swe_scenario = scenarios[0]

    b0 = B0_LiteralTopicBaseline(candidate_reels)
    rec = b0.recommend([swe_scenario.input_reels[0]])
    assert rec.baseline_id == "B0"
    assert rec.recommended_reel_id == "reel_java_syntax_basics"
    assert rec.category == TechCategory.JAVA
    assert 0.0 < rec.score <= 1.0


def test_b1_raw_cosine_similarity_math():
    """Verify B1 baseline computes mathematically exact raw cosine similarity in [-1.0, 1.0]."""
    # Identical vectors -> 1.0
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    assert B1_EmbeddingSemanticSimilarityBaseline.calculate_cosine_similarity(vec_a, vec_b) == 1.0

    # Orthogonal vectors -> 0.0
    vec_c = [0.0, 1.0, 0.0]
    assert B1_EmbeddingSemanticSimilarityBaseline.calculate_cosine_similarity(vec_a, vec_c) == 0.0

    # Opposite vectors -> -1.0 (raw cosine preserved without internal remapping)
    vec_d = [-1.0, 0.0, 0.0]
    assert B1_EmbeddingSemanticSimilarityBaseline.calculate_cosine_similarity(vec_a, vec_d) == -1.0

    # Empty vectors -> 0.0
    assert B1_EmbeddingSemanticSimilarityBaseline.calculate_cosine_similarity([], vec_b) == 0.0

    # Dimension mismatch raises ValueError
    with pytest.raises(ValueError) as exc:
        B1_EmbeddingSemanticSimilarityBaseline.calculate_cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])
    assert "Vector dimension mismatch" in str(exc.value)


def test_b1_provider_injection_and_fake_provider(candidate_reels: list[Reel]):
    """Verify B1 baseline provider injection works and produces deterministic results with FakeEmbeddingProvider."""
    target_cand = candidate_reels[0]
    target_text = B1_EmbeddingSemanticSimilarityBaseline.build_text_representation(target_cand)

    fake_provider = FakeEmbeddingProvider(
        fixed_dim=4,
        preset_embeddings={
            "query": [1.0, 0.0, 0.0, 0.0],
            target_text: [1.0, 0.0, 0.0, 0.0],
        },
    )

    b1 = B1_EmbeddingSemanticSimilarityBaseline(candidate_reels, embedding_provider=fake_provider)
    rec = b1.recommend([target_cand])

    assert rec.baseline_id == "B1"
    assert rec.recommended_reel_id == target_cand.reel_id
    assert rec.score == 1.0
    assert -1.0 <= rec.score <= 1.0


def test_evaluation_harness_requires_explicit_embedding_provider(graph_store: GraphStore):
    """Test 7: EvaluationHarness cannot accidentally run B1 without an explicit provider."""
    # Calling without embedding_provider raises TypeError
    with pytest.raises(TypeError):
        EvaluationHarness(graph_store=graph_store)  # type: ignore[call-arg]

    # Passing None explicitly raises ValueError
    with pytest.raises(ValueError) as exc:
        EvaluationHarness(graph_store=graph_store, embedding_provider=None)  # type: ignore[arg-type]
    assert "An explicit EmbeddingProvider must be provided" in str(exc.value)


def test_real_sentence_transformer_provider_isolated_mocked_execution():
    """Verify real SentenceTransformerEmbeddingProvider configuration and model pinning without network dependency."""
    assert DEFAULT_SENTENCE_TRANSFORMER_MODEL == "sentence-transformers/all-MiniLM-L6-v2"

    provider = SentenceTransformerEmbeddingProvider()
    assert provider.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert provider.device == "cpu"
    assert provider._model is None  # Lazy loading verified

    # Mock the internal model to test embed and embed_batch without network/downloads
    mock_model = MagicMock()
    mock_model.encode.side_effect = lambda texts, **kwargs: (
        [[0.1, 0.2, 0.3, 0.4] for _ in texts] if isinstance(texts, list) else [0.1, 0.2, 0.3, 0.4]
    )
    provider._model = mock_model

    vec = provider.embed("System Design Distributed Caching")
    assert len(vec) == 4
    assert vec == [0.1, 0.2, 0.3, 0.4]

    batch = provider.embed_batch(["Text 1", "Text 2"])
    assert len(batch) == 2
    assert len(batch[0]) == 4


def test_same_candidate_pool_across_all_baselines(harness: EvaluationHarness):
    """Verify B0, B1, and B2 evaluate against the exact same 20-candidate pool."""
    b0_pool_ids = {c.reel_id for c in harness.b0_baseline.candidate_pool}
    b1_pool_ids = {c.reel_id for c in harness.b1_baseline.candidate_pool}
    b2_pool_ids = {c.reel_id for c in harness.candidate_repo.get_all()}

    assert len(b0_pool_ids) == 20
    assert b0_pool_ids == b1_pool_ids == b2_pool_ids


def test_same_scenario_input_across_all_baselines(harness: EvaluationHarness):
    """Verify all baselines receive identical input reel sequences for every scenario."""
    for sc in harness.scenarios:
        assert len(sc.input_reels) == 8
        r0 = harness.b0_baseline.recommend(sc.input_reels)
        r1 = harness.b1_baseline.recommend(sc.input_reels)
        r2, _ = harness.b2_baseline.recommend(student_id=f"test_{sc.scenario_id}", input_reels=sc.input_reels)

        assert r0.recommended_reel_id in harness.candidate_map
        assert r1.recommended_reel_id in harness.candidate_map
        assert r2.recommended_reel_id in harness.candidate_map


def test_ground_truth_isolation_cannot_affect_recommendations(harness: EvaluationHarness):
    """Architectural invariant: Modifying Scenario ground truth fields never changes recommendations."""
    scenarios = get_all_scenarios()
    original_scenario = scenarios[0]

    # Run baseline on original scenario
    rec_b0_orig = harness.b0_baseline.recommend(original_scenario.input_reels)
    rec_b1_orig = harness.b1_baseline.recommend(original_scenario.input_reels)
    rec_b2_orig, _ = harness.b2_baseline.recommend("s_orig", original_scenario.input_reels)

    # Mutate all ground-truth fields
    tampered_scenario = deepcopy(original_scenario)
    tampered_scenario.ground_truth_latent_identity = "TAMPERED_IDENTITY"
    tampered_scenario.ground_truth_target_categories = [TechCategory.OTHER]
    tampered_scenario.literal_trap_categories = [TechCategory.HLD]

    # Run baseline on tampered scenario
    rec_b0_tamp = harness.b0_baseline.recommend(tampered_scenario.input_reels)
    rec_b1_tamp = harness.b1_baseline.recommend(tampered_scenario.input_reels)
    rec_b2_tamp, _ = harness.b2_baseline.recommend("s_orig", tampered_scenario.input_reels)

    # Recommendations must be 100% invariant to ground truth fields
    assert rec_b0_orig.model_dump() == rec_b0_tamp.model_dump()
    assert rec_b1_orig.model_dump() == rec_b1_tamp.model_dump()
    assert rec_b2_orig.model_dump() == rec_b2_tamp.model_dump()


def test_deterministic_repeated_evaluation(harness: EvaluationHarness):
    """Verify repeated benchmark execution produces identical metrics and records."""
    summary_1 = harness.run_benchmark()
    summary_2 = harness.run_benchmark()

    # Compare aggregate metrics
    assert summary_1.aggregate_metrics == summary_2.aggregate_metrics
    assert summary_1.embedding_model_name == "FakeEmbeddingProvider"
    assert summary_1.scenario_count == 4
    assert summary_1.candidate_count == 20

    # Compare per-scenario recommendation decisions
    for r1, r2 in zip(summary_1.scenario_records, summary_2.scenario_records, strict=True):
        assert r1.scenario_id == r2.scenario_id
        for b_id in ("B0", "B1", "B2"):
            assert r1.baseline_recommendations[b_id].model_dump() == r2.baseline_recommendations[b_id].model_dump()
            assert r1.metrics[b_id].model_dump() == r2.metrics[b_id].model_dump()

    # Markdown & JSON reports generate successfully
    report_md = BenchmarkReportGenerator.generate_markdown_report(summary_1)
    assert "# ScrollSense Empirical Evaluation Benchmark Report" in report_md
    assert "B0: Literal Jaccard" in report_md
    assert "B1: Semantic Similarity" in report_md
    assert "B2: ScrollSense (Ours)" in report_md

    report_json = BenchmarkReportGenerator.generate_json_report(summary_1)
    assert '"embedding_model_name": "FakeEmbeddingProvider"' in report_json
