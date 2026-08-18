"""Domain enumerations for ScrollSense v4."""

from enum import StrEnum


class DepthLevel(StrEnum):
    """Learning depth / complexity level."""

    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class NodeType(StrEnum):
    """Types of nodes in the Identity/Skill Graph."""

    TOPIC = "topic"
    SKILL = "skill"
    PROFESSIONAL_IDENTITY = "professional_identity"
    CAREER_STAGE = "career_stage"
    DOMAIN = "domain"


class RelationType(StrEnum):
    """Types of directed relations between nodes in the Identity/Skill Graph."""

    TOPIC_IMPLIES_IDENTITY = "topic_implies_identity"
    IDENTITY_ADJACENT_SKILL = "identity_adjacent_skill"
    SKILL_IMPLIES_ROLE = "skill_implies_role"
    CAREER_STAGE_SIGNAL = "career_stage_signal"
    PROFESSIONAL_IDENTITY_SIGNAL = "professional_identity_signal"
    ADJACENT_TO_ADJACENT = "adjacent_to_adjacent"


class RetrievalSource(StrEnum):
    """Candidate retrieval sources defined in v4 multi-source retrieval."""

    SOURCE_A_TOPICAL = "Source A — Topical"
    SOURCE_B_IDENTITY_ADJACENT = "Source B — 1-hop identity-adjacent"
    SOURCE_C_BOUNDARY_EXPLORATION = "Source C — 2-hop boundary exploration"
    SOURCE_D_REINFORCEMENT = "Source D — Reinforcement"


class ConfidenceBucket(StrEnum):
    """Rule-derived confidence buckets replacing raw floats."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class FeedbackOutcome(StrEnum):
    """Observed viewer interaction outcomes for feedback capture."""

    ACCEPTED = "accepted"
    SKIPPED = "skipped"
    NOT_INTERESTED = "not_interested"
