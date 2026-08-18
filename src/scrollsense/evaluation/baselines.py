"""Baseline recommendation algorithms (B0: Literal Topic, B1: Category Dominance, B2: ScrollSense)."""

from collections import Counter
from typing import Sequence
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import TechCategory
from scrollsense.domain.recommendation import RecommendationOutput
from scrollsense.domain.reels import Reel
from scrollsense.engine import EngineResult, ScrollSenseEngine
from scrollsense.selection.category_mapper import map_reel_to_tech_category


class BaselineRecommendation(BaseModel):
    """Normalized recommendation result produced by an evaluation baseline."""

    model_config = ConfigDict(extra="forbid")

    baseline_id: str = Field(..., description="Baseline identifier (B0, B1, B2)")
    baseline_name: str = Field(..., description="Descriptive name of the baseline algorithm")
    recommended_reel_id: str = Field(..., description="ID of the recommended reel")
    recommended_title: str = Field(..., description="Title of the recommended reel")
    category: TechCategory = Field(..., description="Mapped technical category")
    rationale: str = Field(..., description="Explanation of why this candidate was selected by the baseline")


class B0_LiteralTopicBaseline:
    """Baseline 0: Shallow literal topic/tag matching without latent identity inference."""

    def __init__(self, candidate_pool: Sequence[Reel]) -> None:
        self.candidate_pool = list(candidate_pool)

    def recommend(self, input_reels: Sequence[Reel]) -> BaselineRecommendation:
        """Select candidate with maximum Jaccard concept tag overlap with input reels."""
        if not input_reels:
            raise ValueError("Input reels cannot be empty")

        # Collect all concept tags from input reels, weighting recent reels higher
        input_tags: Counter[str] = Counter()
        for idx, r in enumerate(input_reels):
            weight = (idx + 1) / len(input_reels)
            for t in r.concept_tags:
                input_tags[t.lower()] += weight

        best_score = -1.0
        best_candidate = self.candidate_pool[0]

        for cand in self.candidate_pool:
            cand_tags = set(t.lower() for t in cand.concept_tags)
            overlap_score = sum(input_tags[t] for t in cand_tags)
            if overlap_score > best_score:
                best_score = overlap_score
                best_candidate = cand

        return BaselineRecommendation(
            baseline_id="B0",
            baseline_name="Literal Topic Match",
            recommended_reel_id=best_candidate.reel_id,
            recommended_title=best_candidate.title,
            category=map_reel_to_tech_category(best_candidate),
            rationale=f"Selected based on maximum direct tag/keyword overlap (score {best_score:.2f}) with watched history.",
        )


class B1_CategoryDominanceBaseline:
    """Baseline 1: Shallow category-level recommendation picking first item matching dominant raw category."""

    def __init__(self, candidate_pool: Sequence[Reel]) -> None:
        self.candidate_pool = list(candidate_pool)

    def recommend(self, input_reels: Sequence[Reel]) -> BaselineRecommendation:
        """Find the most frequent raw category in input reels and pick the first matching candidate."""
        if not input_reels:
            raise ValueError("Input reels cannot be empty")

        category_counts = Counter(r.category.lower() for r in input_reels)
        dominant_cat = category_counts.most_common(1)[0][0]

        matching = [c for c in self.candidate_pool if c.category.lower() == dominant_cat]
        selected = matching[0] if matching else self.candidate_pool[0]

        return BaselineRecommendation(
            baseline_id="B1",
            baseline_name="Category Dominance",
            recommended_reel_id=selected.reel_id,
            recommended_title=selected.title,
            category=map_reel_to_tech_category(selected),
            rationale=f"Selected first available candidate matching the dominant watched category '{dominant_cat}'.",
        )


class B2_ScrollSenseBaseline:
    """Baseline 2: Full ScrollSense monolithic recommendation engine."""

    def __init__(self, engine: ScrollSenseEngine) -> None:
        self.engine = engine

    def recommend(self, student_id: str, input_reels: Sequence[Reel]) -> tuple[BaselineRecommendation, EngineResult]:
        """Execute full ScrollSense engine and package into BaselineRecommendation and EngineResult."""
        engine_result = self.engine.recommend_full(student_id=student_id, input_reels=input_reels)
        top_output: RecommendationOutput = engine_result.outputs[0]

        baseline_rec = BaselineRecommendation(
            baseline_id="B2",
            baseline_name="ScrollSense Engine (Ours)",
            recommended_reel_id=engine_result.internal_recommendations[0].reel_id,
            recommended_title=top_output.recommended_tech_reel,
            category=top_output.category,
            rationale=top_output.why_this_recommendation,
        )
        return baseline_rec, engine_result
