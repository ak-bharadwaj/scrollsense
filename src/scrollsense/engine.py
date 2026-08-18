"""Full ScrollSense recommendation engine orchestrating end-to-end inference and ranking."""

from datetime import datetime, timezone
from typing import Sequence
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.candidates import Candidate
from scrollsense.domain.persona import InterestState
from scrollsense.domain.recommendation import Recommendation, RecommendationOutput
from scrollsense.domain.reels import Reel, ReelSignal
from scrollsense.gates.evaluator import CandidateGateEvaluator
from scrollsense.graph.store import GraphStore
from scrollsense.persona.inferencer import PersonaInferencer
from scrollsense.ranking.models import RankingResult
from scrollsense.ranking.ranker import MultiObjectiveRanker
from scrollsense.ranking.weights import RankingWeights
from scrollsense.retrieval.repository import CandidateRepository
from scrollsense.retrieval.retriever import MultiSourceRetriever
from scrollsense.selection.assembler import RecommendationAssembler
from scrollsense.selection.policy import SelectionPolicy
from scrollsense.signals.extractor import DeterministicSignalExtractor, SignalExtractor


class NoEligibleCandidatesError(Exception):
    """Raised when no retrieved candidates survive safety, quality, and ranking gates."""
    pass


class EngineResult(BaseModel):
    """Full traceable audit container for an end-to-end recommendation execution."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(..., description="Target student ID")
    input_reel_ids: list[str] = Field(..., description="IDs of input reels in order")
    extracted_signals: list[ReelSignal] = Field(..., description="Extracted atomic ReelSignals")
    interest_state: InterestState = Field(..., description="Synthesized persona InterestState")
    retrieved_candidates: list[Candidate] = Field(..., description="Retrieved candidate pool")
    ranking_result: RankingResult = Field(..., description="Multi-objective ranking result")
    internal_recommendations: list[Recommendation] = Field(..., description="Internal pipeline recommendations")
    outputs: list[RecommendationOutput] = Field(..., description="User-facing recommendation outputs")


class ScrollSenseEngine:
    """Unified monolithic orchestration entry point for the ScrollSense v4 recommender system."""

    def __init__(
        self,
        extractor: SignalExtractor,
        inferencer: PersonaInferencer,
        retriever: MultiSourceRetriever,
        gate_evaluator: CandidateGateEvaluator,
        ranker: MultiObjectiveRanker,
        assembler: RecommendationAssembler,
        candidate_repository: CandidateRepository | dict[str, Reel] | None = None,
    ) -> None:
        self.extractor = extractor
        self.inferencer = inferencer
        self.retriever = retriever
        self.gate_evaluator = gate_evaluator
        self.ranker = ranker
        self.assembler = assembler
        self.candidate_repository = candidate_repository

    @classmethod
    def create_default(
        cls,
        graph_store: GraphStore,
        candidate_repo: CandidateRepository,
        extractor: SignalExtractor | None = None,
        ranking_weights: RankingWeights | None = None,
        selection_policy: SelectionPolicy | None = None,
    ) -> "ScrollSenseEngine":
        """Factory method to construct a fully wired default ScrollSenseEngine."""
        if extractor is not None:
            signal_extractor = extractor
        else:
            import os
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                from scrollsense.signals.llm_extractor import LLMStructuredSignalExtractor
                from scrollsense.signals.provider import GeminiLLMProvider, LLMConfig
                provider = GeminiLLMProvider(config=LLMConfig.from_env())
                signal_extractor = LLMStructuredSignalExtractor(
                    provider=provider,
                    graph=graph_store,
                    fallback_extractor=DeterministicSignalExtractor(),
                )
            else:
                signal_extractor = DeterministicSignalExtractor()
        inferencer = PersonaInferencer()
        retriever = MultiSourceRetriever(repository=candidate_repo, graph_store=graph_store)
        gate_evaluator = CandidateGateEvaluator()
        ranker = MultiObjectiveRanker(weights=ranking_weights, candidate_repository=candidate_repo)
        assembler = RecommendationAssembler(policy=selection_policy, candidate_repository=candidate_repo)

        return cls(
            extractor=signal_extractor,
            inferencer=inferencer,
            retriever=retriever,
            gate_evaluator=gate_evaluator,
            ranker=ranker,
            assembler=assembler,
            candidate_repository=candidate_repo,
        )

    def recommend(
        self,
        student_id: str,
        input_reels: Sequence[Reel],
        generated_at: datetime | None = None,
    ) -> RecommendationOutput:
        """Execute end-to-end recommendation pipeline and return the primary RecommendationOutput."""
        res = self.recommend_full(student_id=student_id, input_reels=input_reels, generated_at=generated_at)
        if not res.outputs:
            raise NoEligibleCandidatesError(
                f"No eligible candidates survived quality gates and ranking for student '{student_id}'"
            )
        return res.outputs[0]

    def recommend_full(
        self,
        student_id: str,
        input_reels: Sequence[Reel],
        generated_at: datetime | None = None,
    ) -> EngineResult:
        """Execute full end-to-end pipeline and return complete provenance and audit traces."""
        if not input_reels:
            raise ValueError("input_reels sequence cannot be empty")

        timestamp = generated_at or datetime.now(timezone.utc)

        # Stage 1: Signal Extraction (Concurrent for low latency)
        if len(input_reels) == 1:
            signals = [self.extractor.extract(input_reels[0], generated_at=timestamp)]
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(8, len(input_reels))) as executor:
                futures = [
                    executor.submit(self.extractor.extract, reel, timestamp)
                    for reel in input_reels
                ]
                signals = [f.result() for f in futures]

        # Stage 2: Persona Inference
        interest_state = self.inferencer.infer_interest_state(
            student_id=student_id,
            reel_signals=signals,
            updated_at=timestamp,
        )

        # Stage 3: Multi-Source Retrieval
        candidates = self.retriever.retrieve_candidates(interest_state)

        # Stage 4: 3-Tier Candidate Integrity Gates
        # Gate evaluation uses full Reel metadata resolved from candidate_repository
        gate_results = {}
        for cand in candidates:
            reel = self._resolve_reel(cand.reel_id)
            gate_results[cand.reel_id] = self.gate_evaluator.evaluate(reel)

        # Stage 5: Multi-Objective Ranking
        ranking_result = self.ranker.rank_candidates(
            candidates=candidates,
            interest_state=interest_state,
            gate_results=gate_results,
        )

        # Stage 6: Diversity Selection & Recommendation Assembly
        internal_recs, user_outputs = self.assembler.select_and_assemble(
            ranking_result=ranking_result,
            interest_state=interest_state,
            input_reels=input_reels,
        )

        return EngineResult(
            student_id=student_id,
            input_reel_ids=[r.reel_id for r in input_reels],
            extracted_signals=signals,
            interest_state=interest_state,
            retrieved_candidates=candidates,
            ranking_result=ranking_result,
            internal_recommendations=internal_recs,
            outputs=user_outputs,
        )

    def _resolve_reel(self, reel_id: str) -> Reel:
        """Resolve Reel object from candidate repository."""
        if isinstance(self.candidate_repository, CandidateRepository):
            r = self.candidate_repository.get_by_id(reel_id)
            if r:
                return r
        elif isinstance(self.candidate_repository, dict) and reel_id in self.candidate_repository:
            return self.candidate_repository[reel_id]

        raise KeyError(f"Could not resolve Reel metadata for reel ID '{reel_id}'")
