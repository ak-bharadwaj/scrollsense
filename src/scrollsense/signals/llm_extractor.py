"""LLM-backed structured semantic ReelSignal extractor."""

from datetime import datetime, timezone

from scrollsense.domain.enums import EvidenceType
from scrollsense.domain.reels import Reel, ReelSignal
from scrollsense.signals.prompt import (
    StructuredExtractionPayload,
    format_extraction_prompt,
)
from scrollsense.signals.provider import LLMProvider, LLMProviderError

SIGNAL_VERSION = "1.0.0"
ONTOLOGY_VERSION = "1.0.0"

DEFAULT_ALLOWED_IDENTITIES = {
    "software_engineer",
    "backend_developer",
    "gamer",
}

DEFAULT_ALLOWED_CAREER_STAGES = {
    "candidate",
}


class ExtractionError(Exception):
    """Base exception for reel signal extraction failures."""


class ExtractionValidationError(ExtractionError):
    """Raised when LLM output violates post-extraction domain contracts or graph schemas."""


class LLMStructuredSignalExtractor:
    """Production semantic extractor leveraging an LLM provider to extract atomic ReelSignal evidence."""

    def __init__(
        self,
        provider: LLMProvider,
        allowed_identities: set[str] | None = None,
        allowed_career_stages: set[str] | None = None,
        signal_version: str = SIGNAL_VERSION,
        ontology_version: str = ONTOLOGY_VERSION,
    ) -> None:
        self.provider = provider
        self.allowed_identities = allowed_identities or DEFAULT_ALLOWED_IDENTITIES
        self.allowed_career_stages = allowed_career_stages or DEFAULT_ALLOWED_CAREER_STAGES
        self.signal_version = signal_version
        self.ontology_version = ontology_version

    def extract(self, reel: Reel, generated_at: datetime | None = None) -> ReelSignal:
        """Extract a structured ReelSignal by prompting the LLM and validating output schemas."""
        timestamp = generated_at or datetime.now(timezone.utc)

        prompt = format_extraction_prompt(
            reel=reel,
            allowed_identities=self.allowed_identities,
            allowed_career_stages=self.allowed_career_stages,
        )

        try:
            raw_data = self.provider.generate_structured_json(
                prompt=prompt,
                schema=StructuredExtractionPayload,
            )
        except Exception as e:
            raise ExtractionError(f"LLM provider failed for reel '{reel.reel_id}': {e}") from e

        # Validate through Pydantic schema
        try:
            payload = StructuredExtractionPayload.model_validate(raw_data)
        except Exception as e:
            raise ExtractionValidationError(
                f"LLM output for reel '{reel.reel_id}' failed schema validation: {e}"
            ) from e

        # Post-LLM semantic validation against graph contracts
        self._validate_evidence_semantics(reel.reel_id, payload)

        return ReelSignal(
            reel_id=reel.reel_id,
            signal_version=self.signal_version,
            ontology_version=self.ontology_version,
            model_version=self.provider.model_name,
            generated_at=timestamp,
            topic=payload.topic,
            format=payload.format,
            tone=payload.tone,
            depth=payload.depth,
            concept_tags=payload.concept_tags,
            interest_evidence=payload.interest_evidence,
        )

    def _validate_evidence_semantics(self, reel_id: str, payload: StructuredExtractionPayload) -> None:
        """Verify that emitted identity and career stage values exist in canonical graph."""
        for ev in payload.interest_evidence:
            if ev.evidence_type in (
                EvidenceType.TOPIC_IMPLIES_IDENTITY,
                EvidenceType.PROFESSIONAL_IDENTITY_SIGNAL,
            ):
                if ev.value not in self.allowed_identities:
                    raise ExtractionValidationError(
                        f"Reel '{reel_id}' LLM output emitted unsupported identity '{ev.value}'. "
                        f"Allowed graph identities: {self.allowed_identities}"
                    )

            elif ev.evidence_type == EvidenceType.CAREER_STAGE_SIGNAL:
                if ev.value not in self.allowed_career_stages:
                    raise ExtractionValidationError(
                        f"Reel '{reel_id}' LLM output emitted unsupported career stage '{ev.value}'. "
                        f"Allowed graph stages: {self.allowed_career_stages}"
                    )

            if ev.weight is not None and not (0.0 <= ev.weight <= 1.0):
                raise ExtractionValidationError(
                    f"Reel '{reel_id}' LLM output emitted out-of-bounds weight {ev.weight}"
                )
