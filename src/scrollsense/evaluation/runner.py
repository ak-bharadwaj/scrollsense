"""Execution runner for the ScrollSense empirical evaluation harness."""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import DepthLevel
from scrollsense.domain.persona import InterestState
from scrollsense.domain.recommendation import RecommendationOutput
from scrollsense.domain.reels import Reel
from scrollsense.engine import EngineResult, ScrollSenseEngine
from scrollsense.evaluation.baselines import (
    B0_LiteralTopicBaseline,
    B1_EmbeddingSemanticSimilarityBaseline,
    B2_ScrollSenseBaseline,
    BaselineRecommendation,
    EmbeddingProvider,
)
from scrollsense.evaluation.candidate_pool import (
    get_evaluation_candidate_reels,
    get_evaluation_candidate_repository,
)
from scrollsense.evaluation.metrics import MetricCalculator, ScenarioMetrics
from scrollsense.evaluation.scenarios import Scenario, get_all_scenarios
from scrollsense.graph.loader import GraphLoader
from scrollsense.graph.store import GraphStore


class ScenarioEvaluationRecord(BaseModel):
    """Detailed audit trace and benchmark evaluation for a single scenario."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(..., description="Scenario identifier")
    scenario_name: str = Field(..., description="Scenario name")
    input_reel_ids: list[str] = Field(..., description="Ordered list of input reel IDs")
    inferred_identity: str | None = Field(default=None, description="Inferred latent identity for ScrollSense")
    inferred_interest_state: dict[str, Any] | None = Field(default=None, description="InterestState dictionary")
    baseline_recommendations: dict[str, BaselineRecommendation] = Field(
        ...,
        description="Map of baseline ID to recommendation result",
    )
    scrollsense_engine_result: dict[str, Any] | None = Field(
        default=None,
        description="Full ScrollSense EngineResult serialized dictionary",
    )
    metrics: dict[str, ScenarioMetrics] = Field(
        ...,
        description="Map of baseline ID to calculated scenario metrics",
    )


class BenchmarkSummary(BaseModel):
    """Aggregate benchmark report across all evaluation scenarios."""

    model_config = ConfigDict(extra="forbid")

    scenario_records: list[ScenarioEvaluationRecord] = Field(..., description="Individual scenario results")
    aggregate_metrics: dict[str, dict[str, float]] = Field(
        ...,
        description="Average metrics keyed by baseline ID (B0, B1, B2)",
    )
    evaluated_at: datetime = Field(..., description="Timestamp of benchmark execution")


class EvaluationHarness:
    """Orchestrates multi-baseline empirical evaluation across standardized test scenarios."""

    def __init__(
        self,
        graph_store: GraphStore,
        scenarios: list[Scenario] | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.graph_store = graph_store
        self.scenarios = scenarios or get_all_scenarios()
        self.candidate_reels = get_evaluation_candidate_reels()
        self.candidate_repo = get_evaluation_candidate_repository()
        self.candidate_map = {r.reel_id: r for r in self.candidate_reels}

        # Initialize Baselines
        self.b0_baseline = B0_LiteralTopicBaseline(self.candidate_reels)
        self.b1_baseline = B1_EmbeddingSemanticSimilarityBaseline(
            self.candidate_reels,
            embedding_provider=embedding_provider,
        )

        # Initialize ScrollSense Engine
        self.engine = ScrollSenseEngine.create_default(
            graph_store=self.graph_store,
            candidate_repo=self.candidate_repo,
        )
        self.b2_baseline = B2_ScrollSenseBaseline(self.engine)

    def _is_hype(self, reel_id: str) -> bool:
        reel = self.candidate_map.get(reel_id)
        if not reel:
            return False
        return "ai_hype" in reel.concept_tags or "career_shortcuts" in reel.concept_tags

    def _is_unsafe(self, reel_id: str) -> bool:
        reel = self.candidate_map.get(reel_id)
        if not reel:
            return False
        return "malware" in reel.concept_tags

    def run_benchmark(self) -> BenchmarkSummary:
        """Run all baselines against all scenarios and compute comprehensive benchmark metrics."""
        records: list[ScenarioEvaluationRecord] = []
        eval_time = datetime.now(timezone.utc)

        for scenario in self.scenarios:
            recs_by_baseline: dict[str, BaselineRecommendation] = {}
            metrics_by_baseline: dict[str, ScenarioMetrics] = {}

            # 1. Evaluate B0: Literal Topic Matching
            b0_rec = self.b0_baseline.recommend(scenario.input_reels)
            recs_by_baseline["B0"] = b0_rec
            metrics_by_baseline["B0"] = MetricCalculator.evaluate(
                scenario=scenario,
                recommendation=b0_rec,
                is_scrollsense=False,
                is_hype_recommendation=self._is_hype(b0_rec.recommended_reel_id),
                is_unsafe_recommendation=self._is_unsafe(b0_rec.recommended_reel_id),
            )

            # 2. Evaluate B1: Category Dominance Matching
            b1_rec = self.b1_baseline.recommend(scenario.input_reels)
            recs_by_baseline["B1"] = b1_rec
            metrics_by_baseline["B1"] = MetricCalculator.evaluate(
                scenario=scenario,
                recommendation=b1_rec,
                is_scrollsense=False,
                is_hype_recommendation=self._is_hype(b1_rec.recommended_reel_id),
                is_unsafe_recommendation=self._is_unsafe(b1_rec.recommended_reel_id),
            )

            # 3. Evaluate B2: ScrollSense Engine
            b2_rec, engine_result = self.b2_baseline.recommend(
                student_id=f"eval_{scenario.scenario_id}",
                input_reels=scenario.input_reels,
            )
            recs_by_baseline["B2"] = b2_rec
            metrics_by_baseline["B2"] = MetricCalculator.evaluate(
                scenario=scenario,
                recommendation=b2_rec,
                is_scrollsense=True,
                is_hype_recommendation=self._is_hype(b2_rec.recommended_reel_id),
                is_unsafe_recommendation=self._is_unsafe(b2_rec.recommended_reel_id),
            )

            # Extract persona identity summary
            ident_label = (
                list(engine_result.interest_state.professional_identity.keys())[0]
                if engine_result.interest_state.professional_identity
                else "None"
            )

            record = ScenarioEvaluationRecord(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.name,
                input_reel_ids=[r.reel_id for r in scenario.input_reels],
                inferred_identity=ident_label,
                inferred_interest_state=engine_result.interest_state.model_dump(),
                baseline_recommendations=recs_by_baseline,
                scrollsense_engine_result=engine_result.model_dump(),
                metrics=metrics_by_baseline,
            )
            records.append(record)

        # 4. Compute Aggregate Averages across Scenarios
        aggregate: dict[str, dict[str, float]] = {}
        for b_id in ("B0", "B1", "B2"):
            b_metrics = [r.metrics[b_id] for r in records]
            num = len(b_metrics)
            aggregate[b_id] = {
                "trap_avoidance_rate": round(sum(m.trap_avoidance_rate for m in b_metrics) / num, 4),
                "technology_relevance": round(sum(m.technology_relevance for m in b_metrics) / num, 4),
                "identity_consistency": round(sum(m.identity_consistency for m in b_metrics) / num, 4),
                "hype_rejection_rate": round(sum(m.hype_rejection_rate for m in b_metrics) / num, 4),
                "safety_rejection_rate": round(sum(m.safety_rejection_rate for m in b_metrics) / num, 4),
                "provenance_completeness": round(sum(m.provenance_completeness for m in b_metrics) / num, 4),
                "deterministic_replay": round(sum(m.deterministic_replay for m in b_metrics) / num, 4),
                "top1_expert_alignment": round(sum(m.top1_expert_alignment for m in b_metrics) / num, 4),
            }

        return BenchmarkSummary(
            scenario_records=records,
            aggregate_metrics=aggregate,
            evaluated_at=eval_time,
        )
