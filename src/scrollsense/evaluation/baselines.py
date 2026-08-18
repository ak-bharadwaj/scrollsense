"""Baseline recommendation algorithms (B0: Literal Jaccard, B1: Pretrained Sentence Embedding, B2: ScrollSense)."""

import math
from typing import Protocol, Sequence
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import TechCategory
from scrollsense.domain.recommendation import RecommendationOutput
from scrollsense.domain.reels import Reel
from scrollsense.engine import EngineResult, ScrollSenseEngine
from scrollsense.selection.category_mapper import map_reel_to_tech_category

# Pinned pretrained sentence-transformer model identifier for semantic embedding baseline
DEFAULT_SENTENCE_TRANSFORMER_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingProvider(Protocol):
    """Protocol interface for dense text embedding providers."""

    def embed(self, text: str) -> list[float]:
        """Generate dense vector embedding for a single text."""
        ...

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate dense vector embeddings for multiple texts."""
        ...


class SentenceTransformerEmbeddingProvider:
    """Pretrained sentence-transformers embedding provider for semantic similarity baseline.

    Uses a pinned open-source Transformer model ('sentence-transformers/all-MiniLM-L6-v2')
    to map raw text into 384-dimensional dense semantic vectors on CPU.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_SENTENCE_TRANSFORMER_MODEL,
        device: str = "cpu",
    ) -> None:
        self.model_name = model_name
        self.device = device
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                self._model = SentenceTransformer(self.model_name, device=self.device)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to load sentence-transformers model '{self.model_name}': {exc}"
                ) from exc
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._load_model()
        vector = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        if hasattr(vector, "tolist"):
            vector = vector.tolist()
        if isinstance(vector, list) and vector and isinstance(vector[0], list):
            vector = vector[0]
        return [float(x) for x in vector]

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        vectors = model.encode(list(texts), convert_to_numpy=True, normalize_embeddings=True)
        if hasattr(vectors, "tolist"):
            vectors = vectors.tolist()
        return [[float(x) for x in row] for row in vectors]


class FakeEmbeddingProvider:
    """Deterministic fake embedding provider for unit tests without network or model downloads."""

    def __init__(
        self,
        fixed_dim: int = 4,
        preset_embeddings: dict[str, list[float]] | None = None,
    ) -> None:
        self.fixed_dim = fixed_dim
        self.preset_embeddings = preset_embeddings or {}

    def embed(self, text: str) -> list[float]:
        if text in self.preset_embeddings:
            return self.preset_embeddings[text]
        # Deterministic vector based on character sum
        char_sum = sum(ord(c) for c in text)
        val = round(((char_sum % 100) / 100.0) * 2.0 - 1.0, 4)
        return [val] * self.fixed_dim

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class BaselineRecommendation(BaseModel):
    """Normalized recommendation result produced by an evaluation baseline."""

    model_config = ConfigDict(extra="forbid")

    baseline_id: str = Field(..., description="Baseline identifier (B0, B1, B2)")
    baseline_name: str = Field(..., description="Descriptive name of the baseline algorithm")
    recommended_reel_id: str = Field(..., description="ID of the recommended reel")
    recommended_title: str = Field(..., description="Title of the recommended reel")
    category: TechCategory = Field(..., description="Mapped technical category")
    score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Underlying score produced by the baseline (Jaccard in [0,1], raw Cosine in [-1,1], or Ranking score in [0,1])",
    )
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
            score=top_score,
            rationale=f"Selected based on maximum concept-tag Jaccard similarity ({top_score:.4f}) against input history.",
        )


class B1_EmbeddingSemanticSimilarityBaseline:
    """Baseline 1: Pretrained Sentence Embedding semantic similarity baseline.

    Uses dense continuous sentence embeddings of reel text (title + transcript + concept tags + category)
    and computes raw cosine similarity between candidate embeddings and the centroid of watched history.
    Does not use ScrollSense graphs, persona inference, gates, or heuristic ranking objectives.
    """

    def __init__(
        self,
        candidate_pool: Sequence[Reel],
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.candidate_pool = list(candidate_pool)
        self.provider = embedding_provider
        self._candidate_embeddings: list[tuple[Reel, list[float]]] = []
        self._precompute_candidate_embeddings()

    @classmethod
    def build_text_representation(cls, reel: Reel) -> str:
        """Build concatenated text representation: title + transcript + concept tags + category."""
        parts = [reel.title]
        if reel.transcript:
            parts.append(reel.transcript)
        if reel.concept_tags:
            parts.append(" ".join(reel.concept_tags))
        parts.append(reel.category)
        return " ".join(parts)

    def _precompute_candidate_embeddings(self) -> None:
        texts = [self.build_text_representation(c) for c in self.candidate_pool]
        embeddings = self.provider.embed_batch(texts)
        self._candidate_embeddings = list(zip(self.candidate_pool, embeddings, strict=True))

    @staticmethod
    def calculate_cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
        """Compute raw cosine similarity between two dense vectors: (u · v) / (||u|| ||v||) in [-1.0, 1.0]."""
        if not vec_a or not vec_b:
            return 0.0
        if len(vec_a) != len(vec_b):
            raise ValueError(f"Vector dimension mismatch: {len(vec_a)} != {len(vec_b)}")

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        raw_cos = dot_product / (norm_a * norm_b)
        # Numerical clamp to valid [-1.0, 1.0] interval
        clamped_cos = max(-1.0, min(1.0, raw_cos))
        return round(clamped_cos, 4)

    def recommend(self, input_reels: Sequence[Reel]) -> BaselineRecommendation:
        """Compute history embedding centroid and select candidate with maximum raw cosine similarity."""
        if not input_reels:
            raise ValueError("Input reels cannot be empty")

        # 1. Compute embeddings for all watched history reels
        history_texts = [self.build_text_representation(r) for r in input_reels]
        history_embeddings = self.provider.embed_batch(history_texts)

        # 2. Compute history centroid vector
        dim = len(history_embeddings[0])
        centroid = [0.0] * dim
        for emb in history_embeddings:
            for d in range(dim):
                centroid[d] += emb[d]
        centroid = [x / len(history_embeddings) for x in centroid]

        # 3. Score all candidates by raw cosine similarity against history centroid
        scored_candidates: list[tuple[float, str, Reel]] = []
        for cand, cand_emb in self._candidate_embeddings:
            cos_sim = self.calculate_cosine_similarity(centroid, cand_emb)
            scored_candidates.append((cos_sim, cand.reel_id, cand))

        # Deterministic sorting: (-cosine_sim, reel_id ascending)
        scored_candidates.sort(key=lambda item: (-item[0], item[1]))

        top_score, _, best_candidate = scored_candidates[0]

        return BaselineRecommendation(
            baseline_id="B1",
            baseline_name="Embedding Semantic Similarity",
            recommended_reel_id=best_candidate.reel_id,
            recommended_title=best_candidate.title,
            category=map_reel_to_tech_category(best_candidate),
            score=top_score,
            rationale=f"Selected based on maximum raw embedding cosine similarity ({top_score:.4f}) with history centroid vector.",
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
            score=final_score,
            rationale=top_output.why_this_recommendation,
        )
        return baseline_rec, engine_result
