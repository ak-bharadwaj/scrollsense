"""Mapping utility from Reel metadata to standard TechCategory domain enum."""

from scrollsense.domain.enums import TechCategory
from scrollsense.domain.reels import Reel

CONCEPT_CATEGORY_MAP: dict[str, TechCategory] = {
    # System Design / HLD
    "system_design": TechCategory.HLD,
    "distributed_systems": TechCategory.HLD,
    "redis": TechCategory.HLD,
    "cache_invalidation": TechCategory.HLD,
    "distributed_caching": TechCategory.HLD,
    # DSA
    "dsa": TechCategory.DSA,
    "binary_trees": TechCategory.DSA,
    "dynamic_programming": TechCategory.DSA,
    "tree_algorithms": TechCategory.DSA,
    # Java
    "java": TechCategory.JAVA,
    "records": TechCategory.JAVA,
    "sealed_classes": TechCategory.JAVA,
    "pattern_matching": TechCategory.JAVA,
    # Cloud
    "kubernetes": TechCategory.CLOUD,
    "cloud_networking": TechCategory.CLOUD,
    "docker": TechCategory.CLOUD,
    "cloud_infrastructure": TechCategory.CLOUD,
    "serverless": TechCategory.CLOUD,
    "kubernetes_orchestration": TechCategory.CLOUD,
    # Cybersecurity
    "cybersecurity": TechCategory.CYBERSECURITY,
    "oauth2": TechCategory.CYBERSECURITY,
    "jwt": TechCategory.CYBERSECURITY,
    "api_security": TechCategory.CYBERSECURITY,
    "oauth_security": TechCategory.CYBERSECURITY,
    # AI
    "transformers": TechCategory.AI,
    "neural_networks": TechCategory.AI,
    "attention_mechanism": TechCategory.AI,
    "ai_architecture": TechCategory.AI,
    "ai_tools": TechCategory.AI,
    "prompt_engineering": TechCategory.AI,
    "transformer_architecture": TechCategory.AI,
    # Hardware
    "mechanical_keyboards": TechCategory.HARDWARE,
    "hardware": TechCategory.HARDWARE,
    "developer_workstation": TechCategory.HARDWARE,
    # Career
    "resume_writing": TechCategory.CAREER,
    "career_prep": TechCategory.CAREER,
    "interview_prep": TechCategory.CAREER,
}


def map_reel_to_tech_category(reel: Reel) -> TechCategory:
    """Derive standard TechCategory from structured category and concept tags."""
    cat_norm = reel.category.lower().strip()

    # 1. Check direct category strings
    if cat_norm in ("system design", "hld"):
        return TechCategory.HLD
    if cat_norm == "dsa":
        return TechCategory.DSA
    if cat_norm == "java":
        return TechCategory.JAVA
    if cat_norm == "cloud":
        return TechCategory.CLOUD
    if cat_norm in ("cybersecurity", "security"):
        return TechCategory.CYBERSECURITY
    if cat_norm == "ai":
        return TechCategory.AI
    if cat_norm in ("hardware", "gadgets"):
        return TechCategory.HARDWARE
    if cat_norm == "career":
        return TechCategory.CAREER

    # 2. Check concept tags
    for tag in reel.concept_tags:
        tag_norm = tag.lower().strip()
        if tag_norm in CONCEPT_CATEGORY_MAP:
            return CONCEPT_CATEGORY_MAP[tag_norm]

    return TechCategory.OTHER
