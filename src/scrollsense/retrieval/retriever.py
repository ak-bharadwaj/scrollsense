"""Multi-source candidate retrieval engine connecting InterestState and GraphStore to candidates."""

from typing import Iterable

from scrollsense.domain.candidates import Candidate
from scrollsense.domain.enums import RetrievalSource
from scrollsense.domain.persona import InterestState
from scrollsense.graph.store import GraphStore
from scrollsense.retrieval.repository import CandidateRepository

SOURCE_PRIORITY: dict[RetrievalSource, int] = {
    RetrievalSource.SOURCE_B_IDENTITY_ADJACENT: 1,
    RetrievalSource.SOURCE_C_BOUNDARY_EXPLORATION: 2,
    RetrievalSource.SOURCE_A_TOPICAL: 3,
    RetrievalSource.SOURCE_D_REINFORCEMENT: 4,
}


class MultiSourceRetriever:
    """Multi-source candidate retriever implementing Sources A, B, C, and D."""

    def __init__(self, repository: CandidateRepository, graph_store: GraphStore) -> None:
        self.repository = repository
        self.graph_store = graph_store

    def retrieve_candidates(self, interest_state: InterestState) -> list[Candidate]:
        """Execute full multi-source candidate retrieval with deduplication and provenance tracking.

        Determinism Rule:
        Deduplicated candidates are ordered primarily by source priority (B > C > A > D),
        secondarily descending by initial path weight/score, and tertiarily by reel_id ascending.
        """
        candidates_a = self.retrieve_source_a_topical(interest_state)
        candidates_b = self.retrieve_source_b_identity_adjacent(interest_state)
        candidates_c = self.retrieve_source_c_boundary_exploration(interest_state)
        candidates_d = self.retrieve_source_d_reinforcement(interest_state)

        all_candidates: list[Candidate] = (
            candidates_b + candidates_c + candidates_a + candidates_d
        )
        return self._deduplicate_and_rank_candidates(all_candidates)

    def retrieve_source_a_topical(self, interest_state: InterestState) -> list[Candidate]:
        """Source A — Topical: matches candidate content against InterestState.domains."""
        candidates: list[Candidate] = []
        for domain, weight in interest_state.domains.items():
            reels = self.repository.find_by_topic_or_domain(domain)
            for reel in reels:
                candidates.append(
                    Candidate(
                        reel_id=reel.reel_id,
                        source=RetrievalSource.SOURCE_A_TOPICAL,
                        matched_node=domain,
                        graph_distance=0,
                        traversal_path=[domain],
                        initial_score=weight,
                        contributing_sources=[RetrievalSource.SOURCE_A_TOPICAL],
                        contributing_paths=[[domain]],
                    )
                )
        return candidates

    def retrieve_source_b_identity_adjacent(self, interest_state: InterestState) -> list[Candidate]:
        """Source B — 1-hop Identity Adjacent: traverses GraphStore 1 hop from inferred identity."""
        candidates: list[Candidate] = []
        for identity_id, identity_weight in interest_state.professional_identity.items():
            if not self.graph_store.has_node(identity_id):
                continue

            traversals = self.graph_store.traverse_1_hop_identity_adjacent(identity_id)
            for trav in traversals:
                matched_reels = self.repository.find_by_skill_node(trav.destination_node)
                for reel in matched_reels:
                    init_score = round(identity_weight * trav.cumulative_weight, 6)
                    candidates.append(
                        Candidate(
                            reel_id=reel.reel_id,
                            source=RetrievalSource.SOURCE_B_IDENTITY_ADJACENT,
                            matched_node=trav.destination_node,
                            graph_distance=1,
                            traversal_path=list(trav.traversal_path),
                            initial_score=init_score,
                            contributing_sources=[RetrievalSource.SOURCE_B_IDENTITY_ADJACENT],
                            contributing_paths=[list(trav.traversal_path)],
                        )
                    )
        return candidates

    def retrieve_source_c_boundary_exploration(self, interest_state: InterestState) -> list[Candidate]:
        """Source C — 2-hop Boundary Exploration: traverses GraphStore 2 hops from inferred identity."""
        candidates: list[Candidate] = []
        for identity_id, identity_weight in interest_state.professional_identity.items():
            if not self.graph_store.has_node(identity_id):
                continue

            traversals = self.graph_store.traverse_2_hop_boundary_exploration(identity_id)
            for trav in traversals:
                matched_reels = self.repository.find_by_skill_node(trav.destination_node)
                for reel in matched_reels:
                    init_score = round(identity_weight * trav.cumulative_weight, 6)
                    candidates.append(
                        Candidate(
                            reel_id=reel.reel_id,
                            source=RetrievalSource.SOURCE_C_BOUNDARY_EXPLORATION,
                            matched_node=trav.destination_node,
                            graph_distance=2,
                            traversal_path=list(trav.traversal_path),
                            initial_score=init_score,
                            contributing_sources=[RetrievalSource.SOURCE_C_BOUNDARY_EXPLORATION],
                            contributing_paths=[list(trav.traversal_path)],
                        )
                    )
        return candidates

    def retrieve_source_d_reinforcement(self, interest_state: InterestState) -> list[Candidate]:
        """Source D — Reinforcement: matches highest-weight already-demonstrated interest domains."""
        if not interest_state.domains:
            return []

        # Find highest-weight domain for reinforcement
        top_domain = max(interest_state.domains.items(), key=lambda item: item[1])[0]
        top_weight = interest_state.domains[top_domain]

        reels = self.repository.find_by_topic_or_domain(top_domain)
        candidates: list[Candidate] = []
        for reel in reels:
            candidates.append(
                Candidate(
                    reel_id=reel.reel_id,
                    source=RetrievalSource.SOURCE_D_REINFORCEMENT,
                    matched_node=top_domain,
                    graph_distance=0,
                    traversal_path=[top_domain],
                    initial_score=top_weight,
                    contributing_sources=[RetrievalSource.SOURCE_D_REINFORCEMENT],
                    contributing_paths=[[top_domain]],
                )
            )
        return candidates

    def _deduplicate_and_rank_candidates(self, candidates: Iterable[Candidate]) -> list[Candidate]:
        """Deduplicate candidates by reel_id while merging provenance and sorting deterministically."""
        merged_by_id: dict[str, Candidate] = {}

        for cand in candidates:
            if cand.reel_id not in merged_by_id:
                # Initialize candidate entry
                merged_by_id[cand.reel_id] = Candidate(
                    reel_id=cand.reel_id,
                    source=cand.source,
                    matched_node=cand.matched_node,
                    graph_distance=cand.graph_distance,
                    traversal_path=list(cand.traversal_path),
                    initial_score=cand.initial_score,
                    contributing_sources=list(cand.contributing_sources),
                    contributing_paths=list(cand.contributing_paths),
                )
            else:
                existing = merged_by_id[cand.reel_id]

                # Merge contributing sources without duplicates
                for src in cand.contributing_sources:
                    if src not in existing.contributing_sources:
                        existing.contributing_sources.append(src)

                # Merge contributing paths without duplicates
                for path in cand.contributing_paths:
                    if path not in existing.contributing_paths:
                        existing.contributing_paths.append(path)

                # If the incoming candidate has higher source priority, update primary source and traversal metadata
                if SOURCE_PRIORITY[cand.source] < SOURCE_PRIORITY[existing.source]:
                    existing.source = cand.source
                    existing.matched_node = cand.matched_node
                    existing.graph_distance = cand.graph_distance
                    existing.traversal_path = list(cand.traversal_path)
                    existing.initial_score = cand.initial_score

        result = list(merged_by_id.values())

        # Sort deterministically:
        # 1. Source priority rank (1 = Source B, 2 = Source C, 3 = Source A, 4 = Source D)
        # 2. Initial score descending
        # 3. Reel ID ascending
        result.sort(
            key=lambda c: (
                SOURCE_PRIORITY[c.source],
                -(c.initial_score if c.initial_score is not None else 0.0),
                c.reel_id,
            )
        )
        return result
