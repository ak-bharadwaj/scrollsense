"""Deterministic multi-objective candidate ranker."""

from typing import Sequence

from scrollsense.domain.candidates import Candidate
from scrollsense.domain.enums import DepthLevel, RetrievalSource
from scrollsense.domain.gates import GateResult
from scrollsense.domain.persona import InterestState
from scrollsense.domain.ranking import ObjectiveScores
from scrollsense.domain.reels import Reel
from scrollsense.ranking.models import RankedCandidate, RankingResult, RankingTrace
from scrollsense.ranking.weights import RankingWeights
from scrollsense.retrieval.repository import CandidateRepository

DEPTH_NUMERIC: dict[DepthLevel, int] = {
    DepthLevel.BEGINNER: 1,
    DepthLevel.INTERMEDIATE: 2,
    DepthLevel.ADVANCED: 3,
}

CORE_ENGINEERING_CONCEPTS = {
    "system_design",
    "distributed_systems",
    "redis",
    "cache_invalidation",
    "dsa",
    "binary_trees",
    "dynamic_programming",
    "kubernetes",
    "cloud_networking",
    "docker",
    "microservices",
    "cybersecurity",
    "oauth2",
    "jwt",
    "api_security",
    "transformers",
    "neural_networks",
    "attention_mechanism",
    "ai_architecture",
}


class MultiObjectiveRanker:
    """Ranks surviving candidates across 6 normalized heuristic objectives."""

    def __init__(
        self,
        weights: RankingWeights | None = None,
        candidate_repository: CandidateRepository | dict[str, Reel] | None = None,
    ) -> None:
        self.weights = weights or RankingWeights()
        self.candidate_repository = candidate_repository

    def _resolve_reel(
        self,
        candidate: Candidate,
        reels_map: dict[str, Reel] | None = None,
    ) -> Reel:
        """Resolve full Reel metadata for candidate."""
        if reels_map and candidate.reel_id in reels_map:
            return reels_map[candidate.reel_id]

        if isinstance(self.candidate_repository, CandidateRepository):
            r = self.candidate_repository.get_by_id(candidate.reel_id)
            if r:
                return r
        elif isinstance(self.candidate_repository, dict) and candidate.reel_id in self.candidate_repository:
            return self.candidate_repository[candidate.reel_id]

        raise KeyError(
            f"Could not resolve Reel metadata for candidate ID '{candidate.reel_id}'. "
            f"Ensure candidate_repository is provided to MultiObjectiveRanker."
        )

    def rank_candidates(
        self,
        candidates: Sequence[Candidate],
        interest_state: InterestState,
        gate_results: dict[str, GateResult] | Sequence[GateResult],
        reels_map: dict[str, Reel] | None = None,
    ) -> RankingResult:
        """Score and rank candidates that survived safety and quality gates."""
        if isinstance(gate_results, dict):
            gate_map = gate_results
        else:
            gate_map = {gr.candidate_id: gr for gr in gate_results}

        eligible_ranked: list[RankedCandidate] = []
        ineligible_traces: list[RankingTrace] = []

        for cand in candidates:
            r_id = cand.reel_id
            gate_res = gate_map.get(r_id)
            if gate_res is None:
                raise KeyError(f"Missing GateResult for candidate '{r_id}'")

            reel = self._resolve_reel(cand, reels_map)

            # 1. Check eligibility: hard safety rejection or low-substance/high-hype
            if not gate_res.passed or not gate_res.safety.passed:
                obj_scores = self._compute_objective_scores(cand, reel, interest_state, gate_res)
                trace = RankingTrace(
                    candidate_id=r_id,
                    eligible=False,
                    objective_scores=obj_scores,
                    weights=self.weights,
                    weighted_contributions={},
                    final_score=0.0,
                    gate_result=gate_res,
                )
                ineligible_traces.append(trace)
                continue

            # 2. Compute 6 objectives
            obj_scores = self._compute_objective_scores(cand, reel, interest_state, gate_res)

            # 3. Calculate weighted contributions
            topical_contrib = round(self.weights.topical_fit * obj_scores.topical_fit, 4)
            diff_contrib = round(self.weights.difficulty_match * obj_scores.difficulty_match, 4)
            career_contrib = round(self.weights.career_relevance * obj_scores.career_relevance, 4)
            nov_contrib = round(self.weights.novelty * obj_scores.novelty, 4)
            qual_contrib = round(self.weights.quality * obj_scores.quality, 4)
            hype_penalty_contrib = round(-self.weights.hype_penalty * obj_scores.hype_penalty, 4)

            contributions = {
                "topical_fit": topical_contrib,
                "difficulty_match": diff_contrib,
                "career_relevance": career_contrib,
                "novelty": nov_contrib,
                "quality": qual_contrib,
                "hype_penalty": hype_penalty_contrib,
            }

            raw_sum = (
                topical_contrib
                + diff_contrib
                + career_contrib
                + nov_contrib
                + qual_contrib
                + hype_penalty_contrib
            )
            final_score = max(0.0, min(1.0, round(raw_sum, 4)))

            scores_with_final = ObjectiveScores(
                topical_fit=obj_scores.topical_fit,
                difficulty_match=obj_scores.difficulty_match,
                career_relevance=obj_scores.career_relevance,
                novelty=obj_scores.novelty,
                quality=obj_scores.quality,
                hype_penalty=obj_scores.hype_penalty,
                final_score=final_score,
            )

            trace = RankingTrace(
                candidate_id=r_id,
                eligible=True,
                objective_scores=scores_with_final,
                weights=self.weights,
                weighted_contributions=contributions,
                final_score=final_score,
                gate_result=gate_res,
            )

            eligible_ranked.append(
                RankedCandidate(
                    candidate=cand,
                    scores=scores_with_final,
                    final_score=final_score,
                    trace=trace,
                )
            )

        # 4. Deterministic tie-break sorting:
        # 1st: final_score descending
        # 2nd: novelty score descending
        # 3rd: candidate_id ascending
        eligible_ranked.sort(
            key=lambda rc: (-rc.final_score, -rc.scores.novelty, rc.candidate.reel_id)
        )

        return RankingResult(
            ranked_candidates=eligible_ranked,
            ineligible_traces=ineligible_traces,
        )

    def _compute_objective_scores(
        self,
        candidate: Candidate,
        reel: Reel,
        interest_state: InterestState,
        gate_res: GateResult,
    ) -> ObjectiveScores:
        """Compute the individual normalized [0, 1] objective scores."""
        topical = self._compute_topical_fit(reel, interest_state)
        diff = self._compute_difficulty_match(reel, interest_state)
        career = self._compute_career_relevance(reel, interest_state)
        nov = self._compute_novelty(candidate, reel, interest_state)
        qual = gate_res.quality.overall
        hype = gate_res.hype.overall

        return ObjectiveScores(
            topical_fit=topical,
            difficulty_match=diff,
            career_relevance=career,
            novelty=nov,
            quality=qual,
            hype_penalty=hype,
        )

    def _compute_topical_fit(self, reel: Reel, state: InterestState) -> float:
        """Measure compatibility between candidate concept/category and demonstrated domains."""
        if not state.domains:
            return 0.30

        cat_norm = reel.category.lower().replace(" ", "_")
        tags = set(t.lower() for t in reel.concept_tags)

        best_match = 0.0

        backend_tags = {"system_design", "distributed_systems", "redis", "cache_invalidation"}
        cloud_tags = {"kubernetes", "cloud_networking", "docker", "microservices"}
        security_tags = {"cybersecurity", "oauth2", "jwt", "api_security"}
        dsa_tags = {"dsa", "binary_trees", "dynamic_programming"}
        ai_tags = {"transformers", "neural_networks", "attention_mechanism", "ai_architecture"}

        # Direct domain match
        for dom, weight in state.domains.items():
            dom_norm = dom.lower()
            if dom_norm == cat_norm or dom_norm in tags:
                best_match = max(best_match, weight)
            elif dom_norm == "backend" and (cat_norm in ("system_design", "hld") or tags.intersection(backend_tags)):
                best_match = max(best_match, weight * 0.95)
            elif dom_norm == "cloud_infrastructure" and tags.intersection(cloud_tags):
                best_match = max(best_match, weight * 0.90)
            elif dom_norm == "coding" and tags.intersection(CORE_ENGINEERING_CONCEPTS):
                best_match = max(best_match, weight * 0.85)

        # Baseline topical score
        if best_match > 0.0:
            return min(1.0, round(best_match, 4))

        # Fallback for technology candidates when user has tech domains
        has_tech_domain = any(d in ("coding", "backend", "java", "hardware", "ai") for d in state.domains)
        if has_tech_domain and (cat_norm == "coding" or tags.intersection(CORE_ENGINEERING_CONCEPTS)):
            return 0.45

        return 0.10

    def _compute_difficulty_match(self, reel: Reel, state: InterestState) -> float:
        """Compare candidate depth against InterestState depth, rewarding the next logical learning step."""
        user_depth = DepthLevel.BEGINNER
        cat_norm = reel.category.lower().replace(" ", "_")

        # Check domain-specific depth or fall back to overall depth
        if cat_norm in state.depth:
            user_depth = state.depth[cat_norm]
        elif "backend" in state.depth:
            user_depth = state.depth["backend"]
        elif "coding" in state.depth:
            user_depth = state.depth["coding"]
        elif state.depth:
            user_depth = max(state.depth.values(), key=lambda d: DEPTH_NUMERIC[d])

        user_level = DEPTH_NUMERIC[user_depth]
        cand_level = DEPTH_NUMERIC[reel.depth]

        # Ideal progression matrix:
        if user_level == 1:  # User is Beginner
            if cand_level == 1:  # Beginner
                return 0.85
            elif cand_level == 2:  # Intermediate (+1 step: ideal zone of proximal development)
                return 1.00
            else:  # Advanced (+2 step: too steep)
                return 0.45

        elif user_level == 2:  # User is Intermediate
            if cand_level == 2:  # Intermediate
                return 0.95
            elif cand_level == 3:  # Advanced (+1 step: ideal)
                return 1.00
            else:  # Beginner (-1 step: basic review)
                return 0.60

        else:  # User is Advanced
            if cand_level == 3:  # Advanced
                return 1.00
            elif cand_level == 2:  # Intermediate
                return 0.70
            else:  # Beginner
                return 0.35

    def _compute_career_relevance(self, reel: Reel, state: InterestState) -> float:
        """Compute contextual career relevance from goals + professional_identity + concepts."""
        career_prep_goal = state.goals.get("career_prep", 0.0)
        swe_weight = max(
            state.professional_identity.get("software_engineer", 0.0),
            state.professional_identity.get("backend_developer", 0.0),
        )
        gamer_weight = state.professional_identity.get("gamer", 0.0)

        tags = set(t.lower() for t in reel.concept_tags)
        cat_norm = reel.category.lower()

        has_core_eng_concepts = bool(tags.intersection(CORE_ENGINEERING_CONCEPTS))

        # 1. If user has strong SWE identity
        if swe_weight >= 0.50:
            if has_core_eng_concepts or cat_norm in ("system design", "hld", "dsa", "cloud", "cybersecurity"):
                return min(1.0, round(swe_weight * 0.80 + career_prep_goal * 0.20, 4))
            elif "java" in tags or cat_norm == "java":
                return min(1.0, round(swe_weight * 0.45 + career_prep_goal * 0.15, 4))
            elif "software_engineer" in tags or "career_prep" in tags:
                return min(1.0, round(swe_weight * 0.70 + career_prep_goal * 0.30, 4))
            elif cat_norm in ("gaming", "gadgets"):
                return 0.05

        # 2. If user is purely a gamer (no SWE career relevance)
        if gamer_weight >= 0.50 and swe_weight < 0.30:
            if cat_norm in ("gaming", "gadgets") or "fps_gaming" in tags or "esports" in tags:
                return 0.90
            else:
                return 0.05

        # 3. Baseline for unspecialized or candidate goals
        if career_prep_goal > 0.0 and (has_core_eng_concepts or cat_norm == "coding"):
            return min(1.0, round(0.50 + career_prep_goal * 0.40, 4))

        return 0.25

    def _compute_novelty(self, candidate: Candidate, reel: Reel, state: InterestState) -> float:
        """Reward candidates that move beyond literal repeated topics while remaining grounded."""
        if candidate.source == RetrievalSource.SOURCE_C_BOUNDARY_EXPLORATION:
            return 0.95
        elif candidate.source == RetrievalSource.SOURCE_B_IDENTITY_ADJACENT:
            return 0.85
        elif candidate.source == RetrievalSource.SOURCE_A_TOPICAL:
            cat_norm = reel.category.lower()
            if cat_norm in state.domains or "java" in state.domains:
                return 0.30
            return 0.50

        return 0.50
