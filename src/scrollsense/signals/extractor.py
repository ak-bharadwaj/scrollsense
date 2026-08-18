"""Semantic ReelSignal extraction interface and deterministic baseline extractor."""

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from scrollsense.domain.enums import EvidenceType
from scrollsense.domain.reels import InterestEvidence, Reel, ReelSignal

SIGNAL_VERSION = "1.0.0"
ONTOLOGY_VERSION = "1.0.0"
MODEL_VERSION = "rule-based-baseline-v1"


@runtime_checkable
class SignalExtractor(Protocol):
    """Protocol for extracting semantic ReelSignals and InterestEvidence from structured Reel metadata."""

    def extract(self, reel: Reel, generated_at: datetime | None = None) -> ReelSignal:
        """Extract a structured ReelSignal containing atomic interest evidence from a Reel."""
        ...


class DeterministicSignalExtractor:
    """Deterministic baseline extractor converting structured Reel metadata into ReelSignal evidence."""

    def __init__(
        self,
        signal_version: str = SIGNAL_VERSION,
        ontology_version: str = SIGNAL_VERSION,
        model_version: str = MODEL_VERSION,
    ) -> None:
        self.signal_version = signal_version
        self.ontology_version = ontology_version
        self.model_version = model_version

    def extract(self, reel: Reel, generated_at: datetime | None = None) -> ReelSignal:
        """Extract a strongly-typed ReelSignal using multi-feature structured heuristics.

        Evaluates structured combination of:
        category + format + tone + depth + concept_tags
        """
        timestamp = generated_at or datetime.now(timezone.utc)

        # 1. Derive canonical topic representation
        topic = self._derive_topic(reel)

        # 2. Extract atomic multi-signal evidence aligned with Identity/Skill Graph
        evidence = self._extract_interest_evidence(reel)

        return ReelSignal(
            reel_id=reel.reel_id,
            signal_version=self.signal_version,
            ontology_version=self.ontology_version,
            model_version=self.model_version,
            generated_at=timestamp,
            topic=topic,
            format=reel.format or "general",
            tone=reel.tone or "informative",
            depth=reel.depth,
            concept_tags=list(reel.concept_tags),
            interest_evidence=evidence,
        )

    def _derive_topic(self, reel: Reel) -> str:
        """Derive standard normalized topic from structured category and concept tags."""
        tags = set(reel.concept_tags)
        if "java" in tags:
            return "java_meme" if reel.category == "programming_memes" else "java"
        if "software_engineering" in tags or "workplace_culture" in tags:
            return "swe_lifestyle"
        if "coding_interviews" in tags or ("dsa" in tags and reel.category == "career"):
            return "interview_joke" if reel.format == "interview_joke" else "dsa"
        if "developer_workstation" in tags or "docker" in tags:
            return "laptop_comparison"
        if "fps_gaming" in tags or "esports" in tags:
            return "gaming_clip"
        if "prompt_engineering" in tags or "ai_tools" in tags:
            return "ai_prompt_hacks"
        if "cloud_infrastructure" in tags or "serverless" in tags:
            return "tech_news_cloud"
        if "linux_cli" in tags:
            return "linux_cli_tricks"
        return reel.category.lower().replace(" ", "_")

    def _extract_interest_evidence(self, reel: Reel) -> list[InterestEvidence]:
        """Extract atomic InterestEvidence pieces using structured combinations of category, format, tone, and tags.

        Note: Every emitted professional_identity value must correspond to a valid node
        in the canonical Identity/Skill Graph (software_engineer, backend_developer, gamer).
        """
        evidence: list[InterestEvidence] = []
        tags = set(t.lower() for t in reel.concept_tags)
        cat = reel.category.lower()
        fmt = (reel.format or "").lower()

        # Rule 1: Java programming memes / error debugging (moderate-to-weak SWE signal)
        if "java" in tags and (cat == "programming_memes" or "exception_handling" in tags or "production_debugging" in tags):
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.TOPIC_IMPLIES_IDENTITY,
                value="software_engineer",
                weight=0.65,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="java",
                weight=0.80,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="backend",
                weight=0.60,
            ))

        # Rule 2: Software engineering workplace / lifestyle vlogs (strong SWE + backend identity signal)
        elif "software_engineering" in tags or ("workplace_culture" in tags and cat == "entertainment"):
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.TOPIC_IMPLIES_IDENTITY,
                value="software_engineer",
                weight=0.85,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.PROFESSIONAL_IDENTITY_SIGNAL,
                value="backend_developer",
                weight=0.80,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="backend",
                weight=0.75,
            ))

        # Rule 3: Coding interview jokes & preparation (candidate career stage + SWE identity)
        elif "coding_interviews" in tags or ("career_prep" in tags and ("dsa" in tags or fmt == "interview_joke")):
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.CAREER_STAGE_SIGNAL,
                value="candidate",
                weight=0.80,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.GOAL_SIGNAL,
                value="career_prep",
                weight=0.85,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.TOPIC_IMPLIES_IDENTITY,
                value="software_engineer",
                weight=0.70,
            ))

        # Rule 4: Developer workstation & container virtualization hardware (software_engineer identity in graph)
        elif "developer_workstation" in tags or ("hardware" in tags and ("docker" in tags or "local_development" in tags)):
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.PROFESSIONAL_IDENTITY_SIGNAL,
                value="software_engineer",
                weight=0.70,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="hardware",
                weight=0.60,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="cloud_infrastructure",
                weight=0.50,
            ))

        # Rule 5: Pure gaming and esports clips (gamer identity ONLY, never software_engineer)
        elif cat == "gaming" or "fps_gaming" in tags or "esports" in tags or "competitive_gaming" in tags:
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.TOPIC_IMPLIES_IDENTITY,
                value="gamer",
                weight=0.90,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="gaming",
                weight=0.90,
            ))

        # Rule 6: Grounded AI engineering & transformer neural architectures
        elif "transformers" in tags or "neural_networks" in tags or "attention_mechanism" in tags:
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="ai_engineering",
                weight=0.90,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.TOPIC_IMPLIES_IDENTITY,
                value="software_engineer",
                weight=0.65,
            ))

        # Rule 7: AI tools / prompt commentary
        elif "ai_tools" in tags or "prompt_engineering" in tags:
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="ai",
                weight=0.75,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.TOPIC_IMPLIES_IDENTITY,
                value="software_engineer",
                weight=0.60,
            ))

        # Rule 8: AI hype / get rich quick listicles (emits AI domain only, NOT ai_engineering or SWE)
        elif "ai_hype" in tags or "get_rich_quick" in tags:
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="ai",
                weight=0.60,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.GOAL_SIGNAL,
                value="career_shortcuts",
                weight=0.70,
            ))

        # Rule 9: Cloud infrastructure & DevOps news
        elif "cloud_infrastructure" in tags or "serverless" in tags or "kubernetes" in tags:
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="cloud_infrastructure",
                weight=0.85,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.TOPIC_IMPLIES_IDENTITY,
                value="backend_developer",
                weight=0.75,
            ))

        # Rule 10: Linux CLI utilities
        elif "linux_cli" in tags or "server_troubleshooting" in tags:
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value="backend",
                weight=0.75,
            ))
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.TOPIC_IMPLIES_IDENTITY,
                value="backend_developer",
                weight=0.70,
            ))

        # Fallback for general categories
        else:
            evidence.append(InterestEvidence(
                evidence_type=EvidenceType.DOMAIN_SIGNAL,
                value=cat,
                weight=0.50,
            ))

        return evidence
