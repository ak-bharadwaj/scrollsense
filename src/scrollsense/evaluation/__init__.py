"""Evaluation harness and benchmark comparisons for ScrollSense v4."""

from scrollsense.evaluation.baselines import (
    DEFAULT_SENTENCE_TRANSFORMER_MODEL,
    B0_LiteralTopicBaseline,
    B1_EmbeddingSemanticSimilarityBaseline,
    B2_ScrollSenseBaseline,
    BaselineRecommendation,
    EmbeddingProvider,
    FakeEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
)
from scrollsense.evaluation.candidate_pool import (
    get_evaluation_candidate_reels,
    get_evaluation_candidate_repository,
)
from scrollsense.evaluation.metrics import (
    MetricCalculator,
    ScenarioMetrics,
)
from scrollsense.evaluation.reports import BenchmarkReportGenerator
from scrollsense.evaluation.runner import (
    BenchmarkSummary,
    EvaluationHarness,
    ScenarioEvaluationRecord,
)
from scrollsense.evaluation.scenarios import (
    Scenario,
    get_all_scenarios,
)

__all__ = [
    "DEFAULT_SENTENCE_TRANSFORMER_MODEL",
    "B0_LiteralTopicBaseline",
    "B1_EmbeddingSemanticSimilarityBaseline",
    "B2_ScrollSenseBaseline",
    "BaselineRecommendation",
    "BenchmarkReportGenerator",
    "BenchmarkSummary",
    "EmbeddingProvider",
    "EvaluationHarness",
    "FakeEmbeddingProvider",
    "MetricCalculator",
    "Scenario",
    "ScenarioEvaluationRecord",
    "ScenarioMetrics",
    "SentenceTransformerEmbeddingProvider",
    "get_all_scenarios",
    "get_evaluation_candidate_reels",
    "get_evaluation_candidate_repository",
]
