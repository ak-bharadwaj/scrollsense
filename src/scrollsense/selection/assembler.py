"""Deterministic diversity selection and final recommendation assembly."""

from typing import Sequence

from scrollsense.domain.enums import TechCategory
from scrollsense.domain.persona import InterestState
from scrollsense.domain.recommendation import Recommendation, RecommendationOutput
from scrollsense.domain.reels import Reel
from scrollsense.ranking.models import RankedCandidate, RankingResult
from scrollsense.retrieval.repository import CandidateRepository
from scrollsense.selection.category_mapper import map_reel_to_tech_category
from scrollsense.selection.explainer import DeterministicExplainer
from scrollsense.selection.policy import SelectionPolicy


class RecommendationAssembler:
    """Selects top diverse candidates and packages them into internal and user-facing recommendation outputs."""

    def __init__(
        self,
        policy: SelectionPolicy | None = None,
        candidate_repository: CandidateRepository | dict[str, Reel] | None = None,
        explainer: DeterministicExplainer | None = None,
    ) -> None:
        self.policy = policy or SelectionPolicy()
        self.candidate_repository = candidate_repository
        self.explainer = explainer or DeterministicExplainer(self.policy)

    def _resolve_reel(
        self,
        candidate_id: str,
        reels_map: dict[str, Reel] | None = None,
    ) -> Reel:
        """Resolve Reel metadata for candidate ID."""
        if reels_map and candidate_id in reels_map:
            return reels_map[candidate_id]

        if isinstance(self.candidate_repository, CandidateRepository):
            r = self.candidate_repository.get_by_id(candidate_id)
            if r:
                return r
        elif isinstance(self.candidate_repository, dict) and candidate_id in self.candidate_repository:
            return self.candidate_repository[candidate_id]

        raise KeyError(f"Could not resolve Reel metadata for candidate ID '{candidate_id}'")

    def select_and_assemble(
        self,
        ranking_result: RankingResult,
        interest_state: InterestState,
        input_reels: Sequence[Reel],
        reels_map: dict[str, Reel] | None = None,
    ) -> tuple[list[Recommendation], list[RecommendationOutput]]:
        """Select top diverse candidates and assemble Recommendation and RecommendationOutput schemas."""
        if not ranking_result.ranked_candidates:
            return [], []

        # 1. Greedy diversity selection with category redundancy penalty
        selected_ranked: list[RankedCandidate] = []
        selected_categories: set[TechCategory] = set()

        candidates_pool = list(ranking_result.ranked_candidates)

        while len(selected_ranked) < self.policy.max_recommendations and candidates_pool:
            best_candidate = None
            best_adjusted_score = -1.0
            best_index = -1

            for idx, rc in enumerate(candidates_pool):
                reel = self._resolve_reel(rc.candidate.reel_id, reels_map)
                cat = map_reel_to_tech_category(reel)

                diversity_penalty = (
                    self.policy.category_diversity_penalty if cat in selected_categories else 0.0
                )
                adjusted_score = max(0.0, rc.final_score - diversity_penalty)

                if adjusted_score > best_adjusted_score:
                    best_adjusted_score = adjusted_score
                    best_candidate = rc
                    best_index = idx

            if best_candidate is not None:
                selected_ranked.append(best_candidate)
                chosen_reel = self._resolve_reel(best_candidate.candidate.reel_id, reels_map)
                selected_categories.add(map_reel_to_tech_category(chosen_reel))
                candidates_pool.pop(best_index)
            else:
                break

        # 2. Assemble outputs
        internal_recs: list[Recommendation] = []
        user_facing_outputs: list[RecommendationOutput] = []

        current_reel_title = (
            input_reels[-1].title if input_reels else "Watched History"
        )
        interest_label = (
            list(interest_state.professional_identity.keys())[0].replace("_", " ").title()
            if interest_state.professional_identity
            else "General Technology"
        )

        why_detected = self.explainer.build_why_explanation(interest_state, input_reels)

        for rc in selected_ranked:
            reel = self._resolve_reel(rc.candidate.reel_id, reels_map)
            cat = map_reel_to_tech_category(reel)
            confidence = self.explainer.derive_confidence(interest_state, rc)
            why_this_rec = self.explainer.build_why_this_recommendation(rc, reel, interest_state)

            # Internal domain contract
            internal_rec = Recommendation(
                reel_id=reel.reel_id,
                title=reel.title,
                final_score=rc.final_score,
                confidence=confidence,
                retrieval_source=rc.candidate.source,
                traversal_path=rc.candidate.traversal_path,
                objective_scores=rc.scores,
                explanation=why_this_rec,
                evidence_reel_ids=list(interest_state.evidence),
            )
            internal_recs.append(internal_rec)

            # Problem statement user-facing output
            user_output = RecommendationOutput(
                current_reel=current_reel_title,
                interest_detected=interest_label,
                why=why_detected,
                recommended_tech_reel=reel.title,
                category=cat,
                why_this_recommendation=why_this_rec,
                difficulty=reel.depth,
                confidence=confidence,
            )
            user_facing_outputs.append(user_output)

        return internal_recs, user_facing_outputs
