"""Candidate repository and structured content index for retrieval."""

import json
from pathlib import Path
from typing import Sequence

from scrollsense.domain.reels import Reel

# Normalized concept anchor mapping between graph nodes and candidate concept tags/categories
NODE_CONCEPT_MAPPINGS: dict[str, set[str]] = {
    # 1-hop skill nodes
    "system_design": {"system_design", "distributed_systems", "redis", "cache_invalidation"},
    "dsa": {"dsa", "binary_trees", "dynamic_programming", "interview_prep"},
    "cloud_infrastructure": {"cloud_infrastructure", "kubernetes", "cloud_networking", "docker", "serverless"},
    "cybersecurity": {"cybersecurity", "oauth2", "jwt", "api_security"},
    "ai_engineering": {"ai_architecture", "transformers", "neural_networks", "attention_mechanism"},
    "esports_strategy": {"esports", "fps_gaming", "gaming_setup", "mechanical_keyboards"},
    # 2-hop boundary skill nodes
    "distributed_caching": {"redis", "cache_invalidation", "distributed_systems"},
    "tree_algorithms": {"binary_trees", "dynamic_programming", "dsa"},
    "kubernetes_orchestration": {"kubernetes", "docker", "cloud_networking"},
    "oauth_security": {"oauth2", "jwt", "api_security", "cybersecurity"},
    "transformer_architecture": {"transformers", "attention_mechanism", "neural_networks"},
    # Topic nodes
    "java": {"java", "records", "sealed_classes", "pattern_matching"},
    "java_meme": {"java"},
    "ai": {"ai_tools", "ai_architecture", "transformers", "ai_hype", "prompt_engineering"},
    "career": {"career_prep", "resume_writing", "interview_prep"},
    "gaming": {"gaming_setup", "mechanical_keyboards", "fps_gaming"},
    "gadgets": {"mechanical_keyboards", "gaming_setup", "desk_aesthetic", "hardware"},
    "coding": {"java", "linux_cli", "system_design", "dsa", "kubernetes", "cybersecurity"},
}


class CandidateRepository:
    """In-memory candidate repository with structured indices for rapid deterministic matching."""

    def __init__(self, candidates: Sequence[Reel] = ()) -> None:
        self._by_id: dict[str, Reel] = {}
        self._by_category: dict[str, list[Reel]] = {}
        self._by_tag: dict[str, list[Reel]] = {}
        self._build_indices(candidates)

    def _build_indices(self, candidates: Sequence[Reel]) -> None:
        for reel in candidates:
            self._by_id[reel.reel_id] = reel

            cat_key = reel.category.strip().lower()
            self._by_category.setdefault(cat_key, []).append(reel)

            for tag in reel.concept_tags:
                tag_key = tag.strip().lower()
                self._by_tag.setdefault(tag_key, []).append(reel)

    @classmethod
    def load_from_json(cls, file_path: str | Path) -> "CandidateRepository":
        """Load and parse candidates from a JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Candidates file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        candidates = [Reel.model_validate(item) for item in raw_data]
        return cls(candidates)

    @property
    def total_count(self) -> int:
        """Total number of indexed candidate reels."""
        return len(self._by_id)

    def get_by_id(self, reel_id: str) -> Reel | None:
        """Fetch candidate reel by ID."""
        return self._by_id.get(reel_id)

    def get_all(self) -> list[Reel]:
        """Return all candidate reels sorted by reel_id."""
        return sorted(self._by_id.values(), key=lambda r: r.reel_id)

    def find_by_topic_or_domain(self, domain: str) -> list[Reel]:
        """Find candidates matching a topic or domain by category or concept tags."""
        domain_norm = domain.strip().lower()
        matched: dict[str, Reel] = {}

        # 1. Direct category match
        if domain_norm in self._by_category:
            for reel in self._by_category[domain_norm]:
                matched[reel.reel_id] = reel

        # 2. Concept tag matches via taxonomy/synonym mapping
        target_tags = NODE_CONCEPT_MAPPINGS.get(domain_norm, {domain_norm})
        for tag in target_tags:
            if tag in self._by_tag:
                for reel in self._by_tag[tag]:
                    matched[reel.reel_id] = reel

        return sorted(matched.values(), key=lambda r: r.reel_id)

    def find_by_skill_node(self, skill_node_id: str) -> list[Reel]:
        """Find candidates whose concept_tags or category correspond to a graph skill node."""
        skill_norm = skill_node_id.strip().lower()
        target_tags = NODE_CONCEPT_MAPPINGS.get(skill_norm, {skill_norm})

        matched: dict[str, Reel] = {}
        for tag in target_tags:
            if tag in self._by_tag:
                for reel in self._by_tag[tag]:
                    matched[reel.reel_id] = reel

        # Also check direct category match if skill node aligns with category
        if skill_norm in self._by_category:
            for reel in self._by_category[skill_norm]:
                matched[reel.reel_id] = reel

        return sorted(matched.values(), key=lambda r: r.reel_id)
