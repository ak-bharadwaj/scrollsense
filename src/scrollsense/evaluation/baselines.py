"""Baseline recommendation algorithms (B0: Literal Jaccard, B1: Semantic Cosine Similarity, B2: ScrollSense)."""

from collections import Counter
import math
import re
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
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Underlying similarity or rank score")
    rationale: str = Field(..., description="Explanation of why this candidate was selected by the baseline")


class B0_LiteralTopicBaseline:
    """Baseline 0: Unweighted Jaccard similarity over raw concept-tag sets without latent identity inference."""

    def __init__(self, candidate_pool: Sequence[Reel]) -> None:
        self.candidate_pool = list(candidate_pool)

    @staticmethod
    def calculate_jaccard(set_a: set[str], set_b: set[str]) -> float:
        """Compute exact Jaccard similarity: |A ∩ B| / |A ∪ B|."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a.intersection(set_b))
        union = len(set_a.union(set_b))
        if union == 0:
            return 0.0
        return round(intersection / union, 4)

    def recommend(self, input_reels: Sequence[Reel]) -> BaselineRecommendation:
        """Select candidate with maximum unweighted Jaccard concept tag overlap with input history."""
        if not input_reels:
            raise ValueError("Input reels cannot be empty")

        # Aggregate unique concept tags from all input reels
        input_tag_set: set[str] = set()
        for r in input_reels:
            for t in r.concept_tags:
                input_tag_set.add(t.strip().lower())

        scored_candidates: list[tuple[float, str, Reel]] = []
        for cand in self.candidate_pool:
            cand_tag_set = {t.strip().lower() for t in cand.concept_tags}
            jaccard = self.calculate_jaccard(input_tag_set, cand_tag_set)
            scored_candidates.append((jaccard, cand.reel_id, cand))

        # Deterministic sorting: (-jaccard, reel_id ascending)
        scored_candidates.sort(key=lambda item: (-item[0], item[1]))

        top_score, _, best_candidate = scored_candidates[0]

        return BaselineRecommendation(
            baseline_id="B0",
            baseline_name="Literal Jaccard Match",
            recommended_reel_id=best_candidate.reel_id,
            recommended_title=best_candidate.title,
            category=map_reel_to_tech_category(best_candidate),
            similarity_score=top_score,
            rationale=f"Selected based on maximum concept-tag Jaccard similarity ({top_score:.4f}) against input history.",
        )


class B1_SemanticSimilarityBaseline:
    """Baseline 1: Pure semantic term-vector cosine similarity baseline over text representations."""

    def __init__(self, candidate_pool: Sequence[Reel]) -> None:
        self.candidate_pool = list(candidate_pool)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Extract alphanumeric words from text."""
        return re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())

    @classmethod
    def _build_text_representation(cls, reel: Reel) -> str:
        """Build concatenated text representation: title + transcript + concept tags + category."""
        parts = [reel.title]
        if reel.transcript:
            parts.append(reel.transcript)
        if reel.concept_tags:
            parts.append(" ".join(reel.concept_tags))
        parts.append(reel.category)
        return " ".join(parts)

    @classmethod
    def calculate_cosine_similarity(cls, vec_a: Counter[str], vec_b: Counter[str]) -> float:
        """Compute cosine similarity between two term-frequency counter vectors."""
        if not vec_a or not vec_b:
            return 0.0

        dot_product = sum(count * vec_b.get(term, 0) for term, count in vec_a.items())
        norm_a = math.sqrt(sum(count ** 2 for count in vec_a.values()))
        norm_b = math.sqrt(sum(count ** 2 for count in vec_b.values()))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return round(dot_product / (norm_a * norm_b), 4)

    def recommend(self, input_reels: Sequence[Reel]) -> BaselineRecommendation:
        """Select candidate with maximum cosine similarity between history centroid vector and candidate vector."""
        if not input_reels:
            raise ValueError("Input reels cannot be empty")

        # Build history term vector from all input reels
        history_vec: Counter[str] = Counter()
        for r in input_reels:
            tokens = self._tokenize(self._build_text_representation(r))
            for tok in tokens:
                history_vec[tok] += 1

        scored_candidates: list[tuple[float, str, Reel]] = []
        for cand in self.candidate_pool:
            cand_tokens = self._tokenize(self._build_text_representation(cand))
            cand_vec = Counter(cand_tokens)
            cos_sim = self.calculate_cosine_similarity(history_vec, cand_vec)
            scored_candidates.append((cos_sim, cand.reel_id, cand))

        # Deterministic sorting: (-cosine_sim, reel_id ascending)
        scored_candidates.sort(key=lambda item: (-item[0], item[1]))

        top_score, _, best_candidate = scored_candidates[0]

        return BaselineRecommendation(
            baseline_id="B1",
            baseline_name="Semantic Cosine Similarity",
            recommended_reel_id=best_candidate.reel_id,
            recommended_title=best_candidate.title,
            category=map_reel_to_tech_category(best_candidate),
            similarity_score=top_score,
            rationale=f"Selected based on maximum text semantic cosine similarity ({top_score:.4f}) with history centroid.",
        )


class B2_ScrollSenseBaseline:
    """Baseline 2: Full ScrollSense monolithic recommendation engine."""

    def __init__(self, engine: ScrollSenseEngine) -> None:
        self.engine = engine

    def recommend(self, student_id: str, input_reels: Sequence[Reel]) -> tuple[BaselineRecommendation, EngineResult]:
        """Execute full ScrollSense engine and package into BaselineRecommendation and EngineResult."""
        engine_result = self.engine.recommend_full(student_id=student_id, input_reels=input_reels)
        top_output: RecommendationOutput = engine_result.outputs[0]
        final_score = engine_result.internal_recommendations[0].final_score

        baseline_rec = BaselineRecommendation(
            baseline_id="B2",
            baseline_name="ScrollSense Engine (Ours)",
            recommended_reel_id=engine_result.internal_recommendations[0].reel_id,
            recommended_title=top_output.recommended_tech_reel,
            category=top_output.category,
            similarity_score=final_score,
            rationale=top_output.why_this_recommendation,
        )
        return baseline_rec, engine_result
