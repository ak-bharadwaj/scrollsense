"""End-to-end semantic recommendation pipeline composing signals, persona, and retrieval."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.candidates import Candidate
from scrollsense.domain.enums import RetrievalSource
from scrollsense.domain.persona import InterestState
from scrollsense.domain.reels import Reel, ReelSignal
from scrollsense.persona.inferencer import PersonaInferencer
from scrollsense.retrieval.retriever import MultiSourceRetriever
from scrollsense.signals.extractor import SignalExtractor


class PipelineResult(BaseModel):
    """Structured checkpoint result of the end-to-end semantic pipeline."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(..., description="Target student identifier")
    input_reel_ids: list[str] = Field(..., description="Ordered input reel IDs")
    extracted_signals: list[ReelSignal] = Field(..., description="Extracted atomic ReelSignals")
    interest_state: InterestState = Field(..., description="Aggregated student InterestState")
    candidates: list[Candidate] = Field(..., description="Deduplicated retrieved Candidate reels")

    @property
    def candidate_ids(self) -> list[str]:
        """List of retrieved candidate reel IDs."""
        return [c.reel_id for c in self.candidates]

    @property
    def candidate_sources(self) -> dict[str, list[RetrievalSource]]:
        """Map of candidate reel ID to its contributing retrieval sources."""
        return {c.reel_id: c.contributing_sources for c in self.candidates}

    @property
    def candidate_paths(self) -> dict[str, list[list[str]]]:
        """Map of candidate reel ID to its contributing traversal paths."""
        return {c.reel_id: c.contributing_paths for c in self.candidates}


class SemanticPipelineRunner:
    """Coordinates execution across SignalExtractor, PersonaInferencer, and MultiSourceRetriever."""

    def __init__(
        self,
        extractor: SignalExtractor,
        inferencer: PersonaInferencer,
        retriever: MultiSourceRetriever,
    ) -> None:
        self.extractor = extractor
        self.inferencer = inferencer
        self.retriever = retriever

    def run(
        self,
        student_id: str,
        input_reels: Sequence[Reel],
        generated_at: datetime | None = None,
    ) -> PipelineResult:
        """Execute the end-to-end semantic pipeline for a student given watch history reels."""
        timestamp = generated_at or datetime.now(timezone.utc)

        # 1. Semantic signal extraction
        signals = [
            self.extractor.extract(reel, generated_at=timestamp)
            for reel in input_reels
        ]

        # 2. Persona inference
        interest_state = self.inferencer.infer_interest_state(
            student_id=student_id,
            reel_signals=signals,
            updated_at=timestamp,
        )

        # 3. Multi-source candidate retrieval
        candidates = self.retriever.retrieve_candidates(interest_state)

        return PipelineResult(
            student_id=student_id,
            input_reel_ids=[r.reel_id for r in input_reels],
            extracted_signals=signals,
            interest_state=interest_state,
            candidates=candidates,
        )
