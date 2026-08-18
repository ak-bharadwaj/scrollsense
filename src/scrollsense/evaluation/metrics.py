"""Evaluation metrics calculating trap avoidance, identity consistency, hype filtering, and provenance."""

from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import TechCategory
from scrollsense.evaluation.baselines import BaselineRecommendation
from scrollsense.evaluation.scenarios import Scenario


class ScenarioMetrics(BaseModel):
    """Calculated empirical metrics for a specific baseline evaluated on a single scenario."""

    model_config = ConfigDict(extra="forbid")

    baseline_id: str = Field(..., description="Baseline identifier")
    scenario_id: str = Field(..., description="Scenario identifier")
    trap_avoidance_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="1.0 if the recommendation successfully avoided shallow literal traps",
    )
    technology_relevance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="1.0 if the recommendation is high-substance technology",
    )
    identity_consistency: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="1.0 if the recommendation category matches target latent identity",
    )
    hype_rejection_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="1.0 if the recommended item is clean of exaggerated hype claims",
    )
    safety_rejection_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="1.0 if the recommended item is verified safe and non-malicious",
    )
    provenance_completeness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="1.0 if full graph path, evidence IDs, and gate traces are preserved",
    )
    deterministic_replay: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="1.0 if repeated execution produces byte-for-byte identical output",
    )
    top1_expert_alignment: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="1.0 if the top-1 recommendation aligns with expert ground truth target",
    )


class MetricCalculator:
    """Computes standardized evaluation metrics for baseline recommendations against ground truth scenarios."""

    @staticmethod
    def evaluate(
        scenario: Scenario,
        recommendation: BaselineRecommendation,
        is_scrollsense: bool = False,
        is_hype_recommendation: bool = False,
        is_unsafe_recommendation: bool = False,
        is_deterministic: bool = True,
    ) -> ScenarioMetrics:
        """Compute the 8 evaluation metrics for a single scenario and recommendation."""
        cat = recommendation.category

        # 1. Trap avoidance: 0.0 if category is in literal_trap_categories, else 1.0
        trap_avoidance = 0.0 if cat in scenario.literal_trap_categories else 1.0

        # 2. Technology relevance: 0.0 for entertainment/distractors, 1.0 for genuine tech
        tech_relevance = 1.0 if cat != TechCategory.OTHER else 0.0

        # 3. Identity consistency: 1.0 if category is in acceptable target categories
        identity_match = 1.0 if cat in scenario.ground_truth_target_categories else 0.0

        # 4. Hype rejection: 0.0 if a hype item was recommended, 1.0 if recommendation is clean
        hype_rate = 0.0 if is_hype_recommendation else 1.0

        # 5. Safety rejection: 0.0 if an unsafe item was recommended, 1.0 if safe
        safety_rate = 0.0 if is_unsafe_recommendation else 1.0

        # 6. Provenance completeness: 1.0 for ScrollSense (full graph path + evidence), 0.0 for shallow baselines
        provenance = 1.0 if is_scrollsense else 0.0

        # 7. Deterministic replay
        deterministic = 1.0 if is_deterministic else 0.0

        # 8. Top-1 expert alignment: requires trap avoidance, tech relevance, and identity match
        top1_expert = 1.0 if (trap_avoidance == 1.0 and identity_match == 1.0 and not is_hype_recommendation and not is_unsafe_recommendation) else 0.0

        return ScenarioMetrics(
            baseline_id=recommendation.baseline_id,
            scenario_id=scenario.scenario_id,
            trap_avoidance_rate=trap_avoidance,
            technology_relevance=tech_relevance,
            identity_consistency=identity_match,
            hype_rejection_rate=hype_rate,
            safety_rejection_rate=safety_rate,
            provenance_completeness=provenance,
            deterministic_replay=deterministic,
            top1_expert_alignment=top1_expert,
        )
