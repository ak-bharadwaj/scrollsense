"""Deterministic explanation generation and rule-derived confidence derivation."""

from typing import Sequence

from scrollsense.domain.enums import ConfidenceBucket, RetrievalSource
from scrollsense.domain.persona import InterestState
from scrollsense.domain.reels import Reel
from scrollsense.ranking.models import RankedCandidate
from scrollsense.selection.policy import SelectionPolicy


class DeterministicExplainer:
    """Generates structured, traceable explanations and rule-derived confidence buckets."""

    def __init__(self, policy: SelectionPolicy | None = None) -> None:
        self.policy = policy or SelectionPolicy()

    def derive_confidence(
        self,
        state: InterestState,
        ranked_candidate: RankedCandidate,
        runner_up_candidate: RankedCandidate | None = None,
    ) -> ConfidenceBucket:
        """Derive rule-based confidence bucket deterministically from evidence volume, identity weight, and score margin.

        Note: This is a deterministic heuristic bucket, not a calibrated statistical confidence.
        """
        evidence_count = len(state.evidence)
        top_ident_weight = max(state.professional_identity.values()) if state.professional_identity else 0.0

        # Calculate ranking margin over runner-up
        if runner_up_candidate is not None:
            margin = max(0.0, round(ranked_candidate.final_score - runner_up_candidate.final_score, 4))
        else:
            margin = self.policy.single_candidate_default_margin

        # 1. High confidence: strong multi-reel evidence, strong identity, clear ranking margin
        if (
            evidence_count >= self.policy.high_confidence_evidence_threshold
            and top_ident_weight >= self.policy.high_confidence_weight_threshold
            and ranked_candidate.final_score >= 0.60
            and margin >= self.policy.high_confidence_min_margin
        ):
            return ConfidenceBucket.HIGH

        # 2. Medium confidence: moderate evidence/weight and sufficient separation
        elif (
            (top_ident_weight >= self.policy.medium_confidence_weight_threshold or evidence_count >= 2)
            and margin >= self.policy.medium_confidence_min_margin
        ):
            return ConfidenceBucket.MEDIUM

        # 3. Low confidence: weak evidence or tight/negative margin
        else:
            return ConfidenceBucket.LOW

    def build_why_explanation(
        self,
        state: InterestState,
        input_reels: Sequence[Reel],
    ) -> str:
        """Build evidence-grounded explanation of why the specific persona/interest was detected."""
        if not state.professional_identity:
            return "Detected general technology interest based on initial interaction history."

        top_identity, top_weight = list(state.professional_identity.items())[0]
        ident_formatted = top_identity.replace("_", " ").title()

        # Collect titles of input reels present in state.evidence
        contributing_titles: list[str] = []
        for r in input_reels:
            if r.reel_id in state.evidence:
                contributing_titles.append(f"'{r.title}' ({r.reel_id})")

        evidence_str = "; ".join(contributing_titles) if contributing_titles else "recent interaction patterns"

        domains_str = ", ".join(list(state.domains.keys())[:3])
        goals_str = ", ".join(list(state.goals.keys()))

        parts = [
            f"Detected latent '{ident_formatted}' interest (weight {top_weight:.2f}) from watching: {evidence_str}.",
        ]
        if domains_str:
            parts.append(f"Demonstrated domain interest in {domains_str}.")
        if goals_str:
            parts.append(f"Active career goal: {goals_str}.")

        return " ".join(parts)

    def build_why_this_recommendation(
        self,
        ranked_candidate: RankedCandidate,
        reel: Reel,
        state: InterestState,
    ) -> str:
        """Build rationale explaining how graph traversal and multi-objective scoring justified this recommendation."""
        cand = ranked_candidate.candidate
        path_str = " -> ".join(cand.traversal_path) if cand.traversal_path else cand.source.value
        tags_str = ", ".join(reel.concept_tags)

        source_desc = {
            RetrievalSource.SOURCE_B_IDENTITY_ADJACENT: "1-hop identity-adjacent graph traversal",
            RetrievalSource.SOURCE_C_BOUNDARY_EXPLORATION: "2-hop boundary exploration graph traversal",
            RetrievalSource.SOURCE_A_TOPICAL: "topical baseline retrieval",
            RetrievalSource.SOURCE_D_REINFORCEMENT: "domain reinforcement retrieval",
        }.get(cand.source, "graph retrieval")

        return (
            f"Recommended via {source_desc} ({path_str}) covering technical concepts [{tags_str}]. "
            f"Targeted at {reel.depth.value} difficulty to advance from current depth "
            f"with career relevance {ranked_candidate.scores.career_relevance:.2f} and quality score {ranked_candidate.scores.quality:.2f}."
        )
